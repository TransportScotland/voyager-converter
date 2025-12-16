import os
import xml.etree.ElementTree as ET
from lxml import etree

TXC_NS = 'http://www.transxchange.org.uk/'
NS = {'txc': TXC_NS}

REQUIRED_STRUCTURE = {
    "StopPoints": ["AnnotatedStopPointRef"],
    "Services": ["Service"],
    "JourneyPatternSections": ["JourneyPatternSection"],
    "VehicleJourneys": ["VehicleJourney"],
    "Operators": ["Operator"],
    # Expand as needed
}

REQUIRED_SERVICE_CHILDREN = [
    "ServiceCode",
    "RegisteredOperatorRef",
    "OperatingPeriod",
    "StandardService",
    "Lines",
]

REQUIRED_STD_SERVICE_CHILDREN = [
    "Origin", "Destination", "JourneyPattern"
]

REQUIRED_OPERATINGPROFILE_CHILDREN = [
    "RegularDayType"
]


def get_schema_version_and_xsd(xml_file, txc_schema_21, txc_schema_24):
    """
    Parse the TransXChange file header for SchemaVersion and return (version, xsd path)
    Returns (None, None) if not found.
    """
    try:
        for event, elem in ET.iterparse(xml_file, events=("start",)):
            if elem.tag.endswith("TransXChange"):
                schema_version = elem.attrib.get("SchemaVersion", "")
                if schema_version == "2.1":
                    return schema_version, txc_schema_21
                elif schema_version == "2.4":
                    return schema_version, txc_schema_24
                else:
                    return schema_version, None
    except Exception as e:
        print(f"[{os.path.basename(xml_file)}] Problem reading SchemaVersion: {e}")
    return None, None


def validate_transxchange_schema(xml_file, xsd_files, warnings=None):
    """
    Try validating XML against a list of XSD files.
    Return (True, None) if *any* succeed.
    Return (False, errors) if all fail, with aggregated error logs.
    Errors mentioning 'PrivateCodeType' or a missing RegisteredOperatorRef key
    are added to warnings instead of errors.
    """
    if warnings is None:
        warnings = []
    if not isinstance(xsd_files, list):
        xsd_files = [xsd_files]

    xml_doc = None
    try:
        xml_doc = etree.parse(xml_file)
    except Exception as e:
        return (False, [f"[{os.path.basename(xml_file)}] Could not parse XML file: {e}"])

    all_errors = []
    for xsd_file in xsd_files:
        try:
            with open(xsd_file, 'rb') as schema_f:
                schema_doc = etree.parse(schema_f)
            schema = etree.XMLSchema(schema_doc)
        except Exception as e:
            all_errors.append(f"[{os.path.basename(xml_file)}] [{xsd_file}] Schema file error: {e}")
            continue

        try:
            schema.assertValid(xml_doc)
            return (True, None)
        except etree.DocumentInvalid as e:
            for err in schema.error_log:
                msg = f"[{os.path.basename(xml_file)}] [XSD:{xsd_file}] {err.message} (line {err.line})"
                # Add more patterns here as needed
                if (
                    "PrivateCodeType" in err.message or
                    "No match found for key-sequence ['0'] of keyref '{http://www.transxchange.org.uk/}RegisteredOperatorIdKeyRef'" in err.message
                ):
                    warnings.append(msg)
                else:
                    all_errors.append(msg)
        except Exception as e:
            all_errors.append(f"[{os.path.basename(xml_file)}] [{xsd_file}] XMLSchema exception: {e}")

    return (False, all_errors)


def validate_transxchange_full(xml_file, txc_schema_21, txc_schema_24):
    errors = []
    warnings = []

    # --- AUTO-DETECT XSD from file ---
    schema_version, auto_xsd = get_schema_version_and_xsd(xml_file, txc_schema_21, txc_schema_24)
    if auto_xsd is not None:
        xsd_files = [auto_xsd]
        print(f"Detected SchemaVersion '{schema_version}'—using schema: {auto_xsd}")
    else:
        errors.append(f"[{os.path.basename(xml_file)}] Unable to determine SchemaVersion or XSD for validation.")
        return errors, warnings

    # --- 1. Run schema XSD validation ---
    schema_ok, schema_errors = validate_transxchange_schema(xml_file, xsd_files, warnings)
    if not schema_ok:
        print("Schema validation failed with all provided schemas:")
        for err in schema_errors:
            print("  -", err)
        errors.extend(schema_errors)
        return errors, warnings

    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
    except Exception as e:
        errors.append(f"[{os.path.basename(xml_file)}] Failed to parse XML: {e}")
        return errors, warnings

    # -- 2. Structural checks --
    for section, children in REQUIRED_STRUCTURE.items():
        sec = root.find(f'txc:{section}', NS)
        if sec is None:
            errors.append(f"[{os.path.basename(xml_file)}] Missing section: {section}")
            continue
        for child in children:
            elems = sec.findall(f'txc:{child}', NS)
            if not elems:
                warnings.append(f"[{os.path.basename(xml_file)}] Missing child '{child}' in section '{section}'")

    services_section = root.find('txc:Services', NS)
    if services_section is not None:
        for service in services_section.findall('txc:Service', NS):
            for child_tag in REQUIRED_SERVICE_CHILDREN:
                if service.find(f'txc:{child_tag}', NS) is None:
                    warnings.append(f"[{os.path.basename(xml_file)}] Service missing child: {child_tag}")
            std_service = service.find('txc:StandardService', NS)
            if std_service is not None:
                for std_child in REQUIRED_STD_SERVICE_CHILDREN:
                    if std_service.find(f'txc:{std_child}', NS) is None:
                        warnings.append(f"[{os.path.basename(xml_file)}] StandardService missing child: {std_child}")
                for jp in std_service.findall('txc:JourneyPattern', NS):
                    for jp_field in ["Direction", "JourneyPatternSectionRefs"]:
                        if jp.find(f'txc:{jp_field}', NS) is None:
                            warnings.append(f"[{os.path.basename(xml_file)}] JourneyPattern missing: {jp_field}")
            else:
                errors.append(f"[{os.path.basename(xml_file)}] StandardService section not found; cannot check StandardService structure.")
    else:
        errors.append(f"[{os.path.basename(xml_file)}] Services section not found; cannot check services structure.")

    ops_section = root.find('txc:Operators', NS)
    if ops_section is not None:
        for op in ops_section.findall('txc:Operator', NS):
            for tag in ["OperatorShortName"]:
                if op.find(f'txc:{tag}', NS) is None:
                    warnings.append(f"[{os.path.basename(xml_file)}] Operator missing field: {tag}")

    jps_section = root.find('txc:JourneyPatternSections', NS)
    if jps_section is not None:
        for sec in jps_section.findall('txc:JourneyPatternSection', NS):
            links = sec.findall('txc:JourneyPatternTimingLink', NS)
            if not links:
                warnings.append(f"[{os.path.basename(xml_file)}] JourneyPatternSection without any JourneyPatternTimingLinks")
            for link in links:
                for tag in ["From", "To", "RunTime"]:
                    if link.find(f'txc:{tag}', NS) is None:
                        warnings.append(f"[{os.path.basename(xml_file)}] JourneyPatternTimingLink missing field: {tag}")

    vj_section = root.find('txc:VehicleJourneys', NS)
    if vj_section is not None:
        for vj in vj_section.findall('txc:VehicleJourney', NS):
            for vj_field in ["VehicleJourneyCode", "ServiceRef", "JourneyPatternRef", "DepartureTime", "OperatingProfile"]:
                if vj.find(f'txc:{vj_field}', NS) is None:
                    warnings.append(f"[{os.path.basename(xml_file)}] VehicleJourney missing field: {vj_field}")
            op_profile = vj.find('txc:OperatingProfile', NS)
            if op_profile is not None:
                for child in REQUIRED_OPERATINGPROFILE_CHILDREN:
                    if op_profile.find(f'txc:{child}', NS) is None:
                        warnings.append(f"[{os.path.basename(xml_file)}] OperatingProfile missing: {child}")
            else:
                errors.append(f"[{os.path.basename(xml_file)}] VehicleJourney missing OperatingProfile")

    # -- Reporting --
    if errors:
        print("\nValidation errors found:")
        for line in errors:
            print("  -", line)
    if warnings:
        print("\nValidation warnings found:")
        for line in warnings:
            print("  -", line)
    if not errors and not warnings:
        print(f"[{os.path.basename(xml_file)}] TransXChange file is schema+structure validated—no errors or warnings found.")

    return errors, warnings