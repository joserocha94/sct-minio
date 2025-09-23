#!/bin/bash

input_dir="/home/signstash/mnt/app/sign/input"
output_dir="/home/signstash/mnt/app/sign/output"
backup_dir="/home/signstash/mnt/app/sign/backup"

mkdir -p "$input_dir" "$output_dir" "$backup_dir"

for i in $(seq 1 10000); do
  touch "$input_dir/file_0$i.txt"
  touch "$output_dir/file_0$i.txt"
  touch "$backup_dir/file_0$i.txt"
done

echo "10,000 files created in each directory (input, output, backup)."
