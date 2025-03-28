import os
import argparse
import mmap
import re
import time
import csv

# Pre-compile patterns for efficiency
patterns = [
    b'\x01\x00\x00\x00\xF8\x00\x00\x00',
    b'\x01\x00\x00\x00\xF8\x01\x00\x00',
    b'\x01\x00\x00\x00\xF8\x03\x00\x00',    
    b'\x02\x00\x00\x00\xF8\x01\x00\x00', 
    b'\x02\x00\x00\x00\xF8\x00\x00\x00',
    b'\x02\x00\x00\x00\xF8\x03\x00\x00',    
    b'\x03\x00\x00\x00\xF8\x01\x00\x00', 
    b'\x03\x00\x00\x00\xF8\x00\x00\x00',
    b'\x04\x00\x00\x00\xF8\x00\x00\x00',
    b'\x05\x00\x00\x00\xF8\x00\x00\x00',
]
pattern_re = re.compile(b'|'.join(re.escape(p) for p in patterns))  # Join patterns into one regex

def process_match(match_offset, memory_data, csv_writer):
    """Processes pattern match within memory dump and writes relevant data to CSV."""
    try:
        matched_prefix = memory_data[match_offset:match_offset + 8]
    except IndexError:
        return  

    index = match_offset + 8 

    if matched_prefix:
        extracted_data = ""  
        entry_type = "Potential Browser Activity"

        first_byte = memory_data[index:index+1]
        utf16_attempt = False  

        if first_byte not in (b'\x00', b'\x08', b'\xFF', b'\xD0', b'\x2E', b'\x4F'):
            http_data_start = index
            termination_pattern = re.compile(rb'\x00\x0E|\x00\xE5|\x00\x00')
            match = termination_pattern.search(memory_data[http_data_start:])
            if not match:
                return  
            http_data_end = http_data_start + match.start()

            try:
                extracted_data = ''.join(
                    c for c in memory_data[http_data_start:http_data_end].decode('utf-8', errors='ignore').strip()
                    if c.isprintable()
                )
            except UnicodeDecodeError:
                try:
                    extracted_data = ''.join(
                        c for c in memory_data[http_data_start:http_data_end].decode('utf-16', errors='ignore').replace(' ', '').strip()
                        if c.isprintable()
                    )
                    utf16_attempt = True
                except UnicodeDecodeError:
                    extracted_data = f"[Non-printable: {memory_data[http_data_start:http_data_end].hex()}]"

            # Skip writing if no printable data is found**
            if not extracted_data.strip():
                return  

            index = http_data_end + 2  
            print(f"[+] Potential Browser Activity identified at offset: {index}")

            # Write Extracted Data to CSV**
            csv_writer.writerow([match_offset, entry_type, extracted_data])

def extract_browser_activity(dump_file_path, output_csv_path):
    """Reads the entire file using mmap and processes matches sequentially."""
    start_time = time.time()
    print(f"Processing started at: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time))}\n")

    with open(output_csv_path, 'w', newline='', encoding='utf-8') as csv_file:
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(["Offset", "Type", "Extracted Data"])

        with open(dump_file_path, 'rb') as dump_file:
            with mmap.mmap(dump_file.fileno(), 0, access=mmap.ACCESS_READ) as memory_data:
                match_offsets = sorted(match.start() for match in pattern_re.finditer(memory_data))

                for offset in match_offsets:
                    process_match(offset, memory_data, csv_writer)

    end_time = time.time()
    print(f"\nProcessing completed at: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(end_time))}")
    elapsed_time = end_time - start_time
    hours, remainder = divmod(elapsed_time, 3600)
    minutes, seconds = divmod(remainder, 60)
    print(f"Total execution time: {int(hours):02d}:{int(minutes):02d}:{seconds:.2f}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Extract Potential Tor Browser activity from Memory.')
    parser.add_argument('-i', '--input', type=str, required=True, help='Path to the memory dump file.')
    parser.add_argument('-o', '--output', type=str, required=True, help='Path to the output CSV file.')

    args = parser.parse_args()

    print(r"""
   _____                 _             ______                       _          
  / ____|               | |           |  ____|                     (_)         
 | (___  _ __  _   _  __| | ___ _ __  | |__ ___  _ __ ___ _ __  ___ _  ___ ___ 
  \___ \| '_ \| | | |/ _` |/ _ \ '__| |  __/ _ \| '__/ _ \ '_ \/ __| |/ __/ __|
  ____) | |_) | |_| | (_| |  __/ |    | | | (_) | | |  __/ | | \__ \ | (__\__ \
 |_____/| .__/ \__, |\__,_|\___|_|    |_|  \___/|_|  \___|_| |_|___/_|\___|___/
        | |     __/ |                                                          
        |_|    |___/    

Tor Browser Memory Parser - Potential Browser Activity
Version: 1.0 Feb, 2025
Author: Spyder Forensics Training
Website: www.spyderforensics.com
Course: Host-Based Dark Web Forensics
""")

    if not os.path.isfile(args.input):
        print("The specified memory dump file does not exist.")
    else:
        extract_browser_activity(args.input, args.output)
