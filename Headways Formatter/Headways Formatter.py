import tkinter as tk
from tkinter import filedialog, messagebox
from tkinterdnd2 import DND_FILES, TkinterDnD # Make sure tkinterdnd2 is installed
import pandas as pd
import os
from datetime import datetime
import threading

# --- Global variables ---
original_input_dataframe = None # To store the raw input CSV data
processed_dataframe_formatted = None # To store the fully processed data (after process_df)
last_processed_timestamp = None # To keep filenames consistent for a single run

# --- Determine script directory and ensure Outputs directory exists ---
try:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:
    SCRIPT_DIR = os.getcwd() # Fallback if __file__ is not defined
OUTPUT_DIR = os.path.join(SCRIPT_DIR, 'Outputs')
os.makedirs(OUTPUT_DIR, exist_ok=True)


# --- Function definitions ---
def process_df(df, lookup_df):
    # This function remains the same as your provided "Answer" code
    # It takes a DataFrame, processes it (renames, calculates headways, distances, etc.)
    # and returns the processed DataFrame.

    # Rename all columns to look sensible.
    df = df.rename({
        'Service_Name': 'Service Name',
        'Long_Name': 'Long Name',
        'Line_Name': 'Line Name', # This is important for later filtering if acting on this df
        'Route_ID': 'Route ID',
        'Route_ATCO': 'ATCO',
        'am_rt': 'Running Time (AM)',
        'ip_rt': 'Running Time (IP)',
        'pm_rt': 'Running Time (PM)'
    }, axis=1)

    am_headways, ip_headways, pm_headways, node_pairs_list, total_distances = [], [], [], [], []

    print("Processing each row for headways and distances...")

    for _, row in df.iterrows():
        hdwy_str = str(row.get('Headways', ''))
        times_str = str(row.get('Times', ''))

        hdwy = hdwy_str.split(',') if pd.notna(row.get('Headways')) and hdwy_str else []
        times = times_str.split(',') if pd.notna(row.get('Times')) and times_str else []

        am_headway = next((hdwy[i] for i, t in enumerate(times) if t == '1'), 'N/A')
        ip_headway = next((hdwy[i] for i, t in enumerate(times) if t == '2'), 'N/A')
        pm_headway = next((hdwy[i] for i, t in enumerate(times) if t == '3'), 'N/A')

        am_headways.append(am_headway)
        ip_headways.append(ip_headway)
        pm_headways.append(pm_headway)

        nodes_str = str(row.get('Nodes', ''))
        nodes = nodes_str.split(',') if pd.notna(row.get('Nodes')) and nodes_str else []

        consecutive_pairs = [(nodes[i], nodes[i + 1]) for i in range(len(nodes) - 1)] if len(nodes) > 1 else 'N/A'

        if consecutive_pairs != 'N/A':
            pairs_df = pd.DataFrame(consecutive_pairs, columns=['ANode', 'BNode'])
            pairs_df['ANode'] = pairs_df['ANode'].str.strip().str.replace('-', '', regex=False)
            pairs_df['BNode'] = pairs_df['BNode'].str.strip().str.replace('-', '', regex=False)

            try:
                pairs_df['ANode'] = pairs_df['ANode'].astype(int)
                pairs_df['BNode'] = pairs_df['BNode'].astype(int)
            except ValueError as e:
                print(f"Warning: Could not convert ANode/BNode to int for a row. Error: {e}. Skipping distance calculation for these pairs.")
                node_pairs_list.append('Error in Node ID format')
                total_distances.append('Error')
                continue

            merged_df = pairs_df.merge(lookup_df, on=['ANode', 'BNode'], how='left')
            merged_df['DISTANCE'] = pd.to_numeric(merged_df['DISTANCE'], errors='coerce')
            total_distance = merged_df['DISTANCE'].sum()
            total_distances.append(total_distance if pd.notna(total_distance) else 'N/A')
            node_pairs = list(merged_df.apply(lambda x_row: (int(x_row['ANode']), int(x_row['BNode']), float(x_row['DISTANCE']) if pd.notna(x_row['DISTANCE']) else 'Distance could not be found.'), axis=1))
        else:
            node_pairs = 'N/A'
            total_distances.append('N/A')
        node_pairs_list.append(node_pairs)

    df['AM Headway'] = am_headways
    df['IP Headway'] = ip_headways
    df['PM Headway'] = pm_headways
    df['Node Pairs'] = node_pairs_list
    df['Total Distance'] = total_distances

    print("Ordering columns correctly...")
    desired_columns = [
        'Service Name', 'Long Name', 'Line Name', 'Operator', 'Circular',
        'Direction', 'Mode', 'Route ID', 'Times', 'Headways',
        'AM Headway', 'IP Headway', 'PM Headway', 'Running Time (AM)',
        'Running Time (IP)', 'Running Time (PM)', 'Total Distance', 'ATCO',
        'Nodes', 'Node Pairs'
    ]
    existing_columns_in_order = [col for col in desired_columns if col in df.columns]
    other_columns = [col for col in df.columns if col not in existing_columns_in_order]
    df = df[existing_columns_in_order + other_columns]
    return df

def process_file_thread_task(file_path, lookup_df_global):
    global original_input_dataframe, processed_dataframe_formatted, last_processed_timestamp 
    global select_file_button, remove_lines_button, label
    try:
        # Read the original CSV
        df_input_raw = pd.read_csv(file_path)
        original_input_dataframe = df_input_raw.copy() # Store the raw input

        # Process a copy for the 'headways_patched' version
        df_for_processing = df_input_raw.copy()
        df_processed_output = process_df(df_for_processing, lookup_df_global)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(OUTPUT_DIR, f'headways_patched_run_{timestamp}.xlsx')
        df_processed_output.to_excel(output_path, index=False)

        processed_dataframe_formatted = df_processed_output.copy() # Store the formatted version
        last_processed_timestamp = timestamp

        messagebox.showinfo("Success", f"File processed and 'headways_patched' version saved to:\n{output_path}")
        if remove_lines_button:
             remove_lines_button.config(state=tk.NORMAL)

    except Exception as e:
        messagebox.showerror("Error", f"An error occurred during file processing: {e}")
        original_input_dataframe = None
        processed_dataframe_formatted = None
        last_processed_timestamp = None
        if remove_lines_button:
            remove_lines_button.config(state=tk.DISABLED)
    finally:
        if label:
            label.config(text="Drag and drop a CSV file here or click to select")
        if select_file_button:
            select_file_button.config(state=tk.NORMAL)

def start_file_processing(file_path, lookup_df_global):
    global select_file_button, remove_lines_button, label
    if select_file_button:
        select_file_button.config(state=tk.DISABLED)
    if remove_lines_button: # Disable while processing a new file
        remove_lines_button.config(state=tk.DISABLED)
    if label:
        label.config(text="Processing file...")

    # Pass only necessary arguments
    thread = threading.Thread(target=process_file_thread_task, args=(file_path, lookup_df_global))
    thread.start()

def create_lines_removed_version_task(lines_to_remove_df_global):
    global original_input_dataframe, last_processed_timestamp
    global select_file_button, remove_lines_button, label

    if original_input_dataframe is None:
        messagebox.showwarning("No Data", "No original input data available. Please process a file first.")
        return

    try:
        df_to_filter = original_input_dataframe.copy() # Use the stored ORIGINAL dataframe

        if 'Line_Name' not in lines_to_remove_df_global.columns:
            messagebox.showerror("Configuration Error", "Column 'Line_Name' not found in 'lines_to_remove.csv'.")
            return

        lines_to_remove_list = lines_to_remove_df_global['Line_Name'].tolist()

        # The original_input_dataframe should have 'Line_Name' (underscore) as per typical CSV.
        if 'Line_Name' not in df_to_filter.columns:
            messagebox.showerror("Error", "Column 'Line_Name' not found in the original input data. Cannot remove lines.")
            return

        df_lines_removed = df_to_filter[~df_to_filter['Line_Name'].isin(lines_to_remove_list)]

        timestamp_to_use = last_processed_timestamp if last_processed_timestamp else datetime.now().strftime("%Y%m%d_%H%M%S")
        lines_removed_output_path = os.path.join(OUTPUT_DIR, f'headways_patched_lines_removed_run_{timestamp_to_use}.csv')
        df_lines_removed.to_csv(lines_removed_output_path, index=False)

        messagebox.showinfo("Success", f"'Lines removed' version (from original input) created and saved to:\n{lines_removed_output_path}")

    except Exception as e:
        messagebox.showerror("Error", f"An error occurred while creating 'lines removed' version: {e}")
    finally:
        if label:
            label.config(text="Drag and drop a CSV file here or click to select")
        if select_file_button:
            select_file_button.config(state=tk.NORMAL)
        if remove_lines_button:
            # Re-enable if original data is still valid for another attempt or new file processing
            if original_input_dataframe is not None:
                remove_lines_button.config(state=tk.NORMAL)
            else:
                remove_lines_button.config(state=tk.DISABLED)

def start_create_lines_removed_version(lines_to_remove_df_global):
    global original_input_dataframe, select_file_button, remove_lines_button, label
    if original_input_dataframe is None:
        messagebox.showwarning("No Data", "Please process a file first to capture the original data.")
        return

    if select_file_button:
        select_file_button.config(state=tk.DISABLED)
    if remove_lines_button:
        remove_lines_button.config(state=tk.DISABLED)
    if label:
        label.config(text="Creating 'lines removed' version from original input...")

    thread = threading.Thread(target=create_lines_removed_version_task, args=(lines_to_remove_df_global,))
    thread.start()

def on_drop(event):
    file_path = event.data.strip('{}')
    if os.path.isfile(file_path) and file_path.endswith('.csv'):
        # Pass only lookup_data for initial processing
        start_file_processing(file_path, lookup_data)
    else:
        messagebox.showwarning("Invalid File", "Please drop a single CSV file.")

def open_file_dialog():
    file_path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
    if file_path:
        # Pass only lookup_data for initial processing
        start_file_processing(file_path, lookup_data)

# --- Main script execution ---
if __name__ == "__main__":
    try:
        lookup_data = pd.read_csv(r'\\systra.info\UK_DFS\EDINFILE\ProjectData\GB01T25A28 TMfS 2025 Update\5. Technical\5. Modelling\1.Baseline\04_Bus_Services\CA25_road_links.csv')
        lines_to_remove_data = pd.read_csv(os.path.join(SCRIPT_DIR, 'lines_to_remove.csv'))
    except FileNotFoundError as e:
        messagebox.showerror("Initialization Error", f"Failed to load essential CSV file: {e}.\nPlease ensure 'CA25_road_links.csv' (network path) and 'lines_to_remove.csv' (in script directory) exist.")
        exit()
    except Exception as e:
        messagebox.showerror("Initialization Error", f"An error occurred during initialization: {e}")
        exit()

    root = TkinterDnD.Tk()
    root.title("CSV Processor")

    label = tk.Label(root, text="Drag and drop a CSV file here or click to select", width=60, height=10, bg="lightgray")
    label.pack(padx=10, pady=10)
    label.drop_target_register(DND_FILES)
    label.dnd_bind('<<Drop>>', on_drop)

    select_file_button = tk.Button(root, text="Select CSV File and Process", command=open_file_dialog)
    select_file_button.pack(pady=5)

    remove_lines_button = tk.Button(root, text="Create 'Lines Removed' Version (from Original Input)",
                                    command=lambda: start_create_lines_removed_version(lines_to_remove_data),
                                    state=tk.DISABLED)
    remove_lines_button.pack(pady=5)

    root.mainloop()