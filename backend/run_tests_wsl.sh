#!/bin/bash
cd /mnt/c/Users/visha/OneDrive/Desktop/567/backend
export DATABASE_URL="postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/hospitalai"
python3 -m uvicorn main:app --port 8000 &
SERVER_PID=$!
sleep 5
python3 -m pytest test_chained.py -s -v
TEST_EXIT_CODE=$?
kill $SERVER_PID
exit $TEST_EXIT_CODE
