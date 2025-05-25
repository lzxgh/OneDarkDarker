# string_replacer.py
import yaml
import sys
import shutil
import os
import re
import json
import argparse

def parse_yaml_file(yaml_file_path):
    try:
        with open(yaml_file_path, 'r') as f:
            data = yaml.safe_load(f)
            return data
    except FileNotFoundError:
        print(f"Error: YAML file not found at {yaml_file_path}")
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Error parsing YAML file {yaml_file_path}: {e}")
        sys.exit(1)

def get_yaml_value(data, path_str, theme_name=None):
    original_path_for_not_found = path_str
    if theme_name and path_str.startswith("theme."):
        path_str = theme_name + "." + path_str[len("theme."):]
        original_path_for_not_found = f"theme.{path_str[len(theme_name)+1:]}"

    keys = path_str.split('.')
    current_val = data
    try:
        for key in keys:
            if isinstance(current_val, dict) and key in current_val:
                current_val = current_val[key]
            else:
                print(f"Warning: Path '{path_str}' (resolved from '{original_path_for_not_found}') not found or invalid in YAML data.")
                return f"NOT_FOUND_{original_path_for_not_found}"
        if isinstance(current_val, (dict, list)):
            print(f"Warning: Path '{path_str}' (resolved from '{original_path_for_not_found}') resolves to a collection, not a simple value.")
            return f"NOT_FOUND_INCOMPLETE_PATH_{original_path_for_not_found}"
        return str(current_val)
    except (KeyError, TypeError) as e:
        print(f"Warning: Error accessing path '{path_str}' (resolved from '{original_path_for_not_found}'): {e}")
        return f"NOT_FOUND_{original_path_for_not_found}"

def copy_files(input_dir, output_dir):
    try:
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)

        os.makedirs(output_dir, exist_ok=True)

        for item in os.listdir(input_dir):
            s = os.path.join(input_dir, item)
            d = os.path.join(output_dir, item)
            if os.path.isdir(s):
                shutil.copytree(s, d, symlinks=False, ignore=None)
            else:
                shutil.copy2(s, d)
        print(f"Successfully copied files from '{input_dir}' to '{output_dir}'.")

    except (IOError, OSError) as e:
        print(f"Error copying files from '{input_dir}' to '{output_dir}': {e}")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred during file copying: {e}")
        sys.exit(1)

def replace_strings_in_files(output_dir, yaml_data):
    placeholder_regex = re.compile(r"\{\{(.+?)\}\}")

    for root, _, files_in_dir in os.walk(output_dir):
        for filename in files_in_dir:
            if not (filename.endswith(".xml") or filename.endswith(".json")):
                continue

            filepath = os.path.join(root, filename)
            print(f"Processing file: {filepath}")
            current_theme_name = None
            identified_json_theme_key = False
            identified_xml_theme_comment = False
            xml_theme_comment_string = ""

            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    initial_content = f.read()

                # Detect theme using initial_content
                if filename.endswith(".json"):
                    try:
                        json_content_obj = json.loads(initial_content)
                        if isinstance(json_content_obj, dict) and "_" in json_content_obj:
                            theme_setting_str = json_content_obj["_"]
                            if isinstance(theme_setting_str, str): # Check if the value is a string
                                match_obj = re.search(r"{% set theme=(\w+) %}", theme_setting_str)
                                if match_obj:
                                    current_theme_name = match_obj.group(1)
                                    identified_json_theme_key = True
                                    print(f"  Detected JSON theme: {current_theme_name}")
                            else:
                                print(f"  Warning: '_' key in JSON {filepath} does not contain a string for theme value.")
                    except json.JSONDecodeError as jde:
                        print(f"  Warning: Could not parse initial JSON in {filepath} to detect theme: {jde}")
                    except Exception as e:
                        print(f"  Warning: Error during JSON theme detection for {filepath}: {e}")

                elif filename.endswith(".xml"):
                    if initial_content:
                        first_line_end_index = initial_content.find('\n')
                        first_line = initial_content[:first_line_end_index] if first_line_end_index != -1 else initial_content

                        match_obj = re.search(r"<!-- {% set theme=(\w+) %} -->", first_line)
                        if match_obj:
                            current_theme_name = match_obj.group(1)
                            identified_xml_theme_comment = True
                            xml_theme_comment_string = match_obj.group(0)
                            print(f"  Detected XML theme: {current_theme_name} via comment: '{xml_theme_comment_string}'")

                if current_theme_name:
                    print(f"  Applying theme '{current_theme_name}' for replacements.")
                else: # when no theme is found.
                    print(f"  No theme detected for {filepath}. Skip.")
                    continue


                def replace_callback(match_obj_cb):
                    path_str = match_obj_cb.group(1).strip()
                    return get_yaml_value(yaml_data, path_str, current_theme_name)

                content_after_replacements = placeholder_regex.sub(replace_callback, initial_content)
                final_content = content_after_replacements # Initialize final_content

                # Cleanup for JSON files
                if identified_json_theme_key:
                    try:
                        # Attempt to parse final_content, which should be a string after replacements
                        json_obj_for_cleanup = json.loads(final_content)
                        if isinstance(json_obj_for_cleanup, dict) and "_" in json_obj_for_cleanup:
                            del json_obj_for_cleanup["_"]
                            final_content = json.dumps(json_obj_for_cleanup, indent=2)
                            # Ensure a trailing newline for JSON files if original had one and it's not empty
                            if initial_content.endswith('\n') and final_content and not final_content.endswith('\n'):
                                final_content += '\n'
                            print(f"  Removed '_' key from JSON structure: {filepath}")
                    except json.JSONDecodeError as e:
                        print(f"  Warning: Could not parse JSON for cleanup in {filepath} (content after replacements might be invalid JSON): {e}. Theme key may remain.")

                # Cleanup for XML files
                elif identified_xml_theme_comment:
                    if final_content.startswith(xml_theme_comment_string):
                        # Remove the comment and the newline immediately following it, if any
                        if len(final_content) > len(xml_theme_comment_string) and final_content[len(xml_theme_comment_string)] == '\n':
                            final_content = final_content[len(xml_theme_comment_string) + 1:]
                        else:
                            final_content = final_content[len(xml_theme_comment_string):]

                        # If original content was just the theme comment (possibly with a newline), final should be empty
                        # And if the original initial_content.strip() was just the comment, make final_content empty.
                        if initial_content.strip() == xml_theme_comment_string.strip():
                            final_content = ""
                        # Preserve trailing newline if original file had one and content is not now empty
                        elif initial_content.endswith('\n') and final_content and not final_content.endswith('\n'):
                             final_content += '\n'

                        print(f"  Removed XML theme comment from: {filepath}")
                    else:
                        print(f"  Warning: XML theme comment ('{xml_theme_comment_string}') was identified but not found at the start of content after replacements. XML Cleanup skipped for: {filepath}")

                # Write to file if changes were made (replacements or cleanup)
                if final_content != initial_content:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(final_content)
                    print(f"  Successfully updated and saved: {filepath}")
                else:
                    print(f"  No net changes (replacements or cleanup) made to: {filepath}")
            except Exception as e: # General error handling for the file
                print(f"ERROR processing file {filepath}: {e}")


def main():
    parser = argparse.ArgumentParser(description="Replaces placeholders in XML and JSON files based on a YAML template.")
    parser.add_argument("--yaml-file", "-y", required=True, help="Path to the YAML template file.")
    parser.add_argument("--input-dir", "-i", required=True, help="Path to the input directory.")
    parser.add_argument("--output-dir", "-o", required=True, help="Path to the output directory.")

    args = parser.parse_args()

    print("Starting string replacement process...")

    yaml_data = parse_yaml_file(args.yaml_file)

    copy_files(args.input_dir, args.output_dir)

    replace_strings_in_files(args.output_dir, yaml_data)

    print("String replacement process completed successfully.")

if __name__ == "__main__":
    main()
