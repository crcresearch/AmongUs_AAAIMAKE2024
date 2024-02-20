#!/bin/bash

venv_path="SET_YOUR_ENVIRONMENT"
# Array of models
models=("claude" "gpt4" "llama")

# Loop over each model
for model in "${models[@]}"; do
    # Loop over numbers from 1 to 10
    for number in {1..10}; do
        # Construct the command
        cmd="python3 -u listen.py configs/${model}/${number}.json"

        # Run the command with nohup and redirect output to a log file
        nohup $cmd > "logs/${model}_${number}.log" 2>&1 &

        echo "Started ${model} with number ${number}"
    done
done

echo "All processes started."
