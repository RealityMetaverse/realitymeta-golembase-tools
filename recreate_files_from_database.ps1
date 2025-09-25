# This script sets up the PYTHONPATH and runs the Python module

# Set PYTHONPATH to current directory
$env:PYTHONPATH = $PWD

# Run the Python module with all passed arguments
python -m python.scripts.recreate_files_from_database $args
