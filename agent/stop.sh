#!/bin/bash

# Script to stop the application by PORT

PORT=8004

# Colorful log functions
print_info() {
  echo -e "\e[34m[INFO] $1\e[0m"
}

print_success() {
  echo -e "\e[32m[SUCCESS] $1\e[0m"
}

print_error() {
  echo -e "\e[31m[ERROR] $1\e[0m"
}

# Find PID by port
PID=$(lsof -ti tcp:$PORT)

if [ -z "$PID" ]; then
  print_info "No application is running on port $PORT"
else
  print_info "Stopping application on port $PORT (PID: $PID)..."

  # Kill the process
  kill $PID

  # Wait and force kill if necessary
  sleep 2
  if lsof -i :$PORT > /dev/null; then
    print_info "Application did not stop gracefully. Forcing termination..."
    kill -9 $PID
    sleep 1
  fi

  # Final check
  if lsof -i :$PORT > /dev/null; then
    print_error "Failed to stop the application on port $PORT"
    exit 1
  else
    print_success "Application on port $PORT stopped successfully"
  fi
fi
