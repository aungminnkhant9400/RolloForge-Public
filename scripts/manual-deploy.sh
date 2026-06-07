#!/bin/bash
# Manual deploy script for RolloForge dashboard

cd /home/ubuntu/RolloForge/web

# Ensure data is copied
echo "Copying data files..."
npm run data

# Check files exist
echo "Checking files..."
ls -la public/

echo "Ready for Vercel deploy"
