#!/bin/bash

# run_alziaid.sh
cd ~/AlziAid
source alziaid_venv/bin/activate
python3 main.py || {
    echo "Error: Failed to run main.py. Check ~/AlziAid/app_error.log."
    exit 1
}
echo "Test complete. CSV saved in ~/AlziAid/."
echo "Upload the CSV to [Insert Google Drive Link] or email to [Insert Email]."
