
# Read the file
file_path = "c:\\IMPORTANT FILES\\codes\\wellio\\rppg_streamlit_ui.py"
with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Lines to delete (1-based from view_file, so 0-based is index-1)
# Start: 2868 -> Index 2867
# End: 2936 -> Index 2935 (inclusive) -> Slice up to 2936

# Verify the content before deleting
start_idx = 2867
end_idx = 2936

print(f"Deleting lines {start_idx+1} to {end_idx}:")
print(f"Start content: {lines[start_idx].strip()}")
print(f"End content: {lines[end_idx-1].strip()}")

# Slice the lines
new_lines = lines[:start_idx] + lines[end_idx:]

# Write back
with open(file_path, "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print("File updated successfully.")
