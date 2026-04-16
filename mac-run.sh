#!/bin/bash

# --- Launch Server ---
echo "Re-activating main environment for server launch..."

if [ ! -d "venv" ]; then
    echo "Error: Virtual environment 'venv' not found. Please run ./mac-install.sh first."
    exit 1
fi

source venv/bin/activate

echo ""
echo "###########################################################"
echo "#                                                         #"
echo "#           SUCCESS: Q-ACE Server is Starting!            #"
echo "#                                                         #"
echo "###########################################################"
echo ""
echo " The application is now UP AND RUNNING."
echo ""
echo " 1. Open your browser at: http://localhost:8090"
echo " 2. Login with the default credentials:"
echo ""
echo "    Username: admin"
echo "    Password: admin123"
echo ""
echo "###########################################################"
echo ""

uvicorn main:app --host 0.0.0.0 --port 8090 --reload