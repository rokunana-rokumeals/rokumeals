
file_path = r'd:\Kuliah\SEM 5\KG\Kerkel\templates\mbg_app\detail.html'

# The problematic section starts around line 174 and ends around 210.
# We will read the file, find the start and end markers of the block, and replace it entirely.

start_marker = '<div class="col-md-6">'
end_marker = '</div>' # This is too generic.

# Let's use a more robust approach. We know the structure.
# We will look for the "Nutritional Data (per 100g)" header and the "Vitamins & Minerals" header.

new_nutritional_block = """                                    <div class="col-md-6">
                                        <h6 class="text-secondary">Nutritional Data (per 100g)</h6>
                                        <ul class="list-unstyled">
                                            {% if item.calories_per_100g %}<li><strong>Calories:</strong> {{ item.calories_per_100g }} cal</li>{% endif %}
                                            {% if item.carbohydrates_g %}<li><strong>Carbohydrates:</strong> {{ item.carbohydrates_g }} g</li>{% endif %}
                                            {% if item.protein_g %}<li><strong>Protein:</strong> {{ item.protein_g }} g</li>{% endif %}
                                            {% if item.fat_g %}<li><strong>Fat:</strong> {{ item.fat_g }} g</li>{% endif %}
                                            {% if item.fiber_g %}<li><strong>Fiber:</strong> {{ item.fiber_g }} g</li>{% endif %}
                                            {% if item.sugar_g %}<li><strong>Sugar:</strong> {{ item.sugar_g }} g</li>{% endif %}
                                            {% if item.water_g %}<li><strong>Water:</strong> {{ item.water_g }} g</li>{% endif %}
                                        </ul>
                                    </div>"""

new_vitamins_block = """                                    <div class="col-md-6">
                                        <h6 class="text-secondary">Vitamins & Minerals</h6>
                                        <ul class="list-unstyled">
                                            {% if item.vitamin_c_mg %}<li><strong>Vitamin C:</strong> {{ item.vitamin_c_mg }} mg</li>{% endif %}
                                            {% if item.calcium_mg %}<li><strong>Calcium:</strong> {{ item.calcium_mg }} mg</li>{% endif %}
                                            {% if item.iron_mg %}<li><strong>Iron:</strong> {{ item.iron_mg }} mg</li>{% endif %}
                                            {% if item.sodium_mg %}<li><strong>Sodium:</strong> {{ item.sodium_mg }} mg</li>{% endif %}
                                            {% if item.potassium_mg %}<li><strong>Potassium:</strong> {{ item.potassium_mg }} mg</li>{% endif %}
                                            {% if item.magnesium_mg %}<li><strong>Magnesium:</strong> {{ item.magnesium_mg }} mg</li>{% endif %}
                                        </ul>
                                    </div>"""

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# We will rewrite the file line by line, but when we hit the problematic blocks, we skip lines until we are past them, and insert the new blocks.
# This is risky if we don't match exactly.

# Alternative: Just read the whole content and use regex to replace the specific split patterns again, but be very loose with whitespace.
import re

content = "".join(lines)

# Regex to fix: {% if ... %}...{% \s* endif %}
# The previous regex might have failed if there were other characters or if I messed up the pattern.
# Let's look at the specific failure:
# {% if item.sugar_g %}<li><strong>Sugar:</strong> {{ item.sugar_g }} g</li>{%
#                                             endif %}

# Pattern: `{%` at end of line, `endif %}` at start of next line.
# We want to replace `{%` + whitespace + newline + whitespace + `endif %}` with `{% endif %}`

# Let's try to be very specific about the split tag.
# We want to match `{%` followed by `\s+` (including newlines) and then `endif %}`.
# But we only want to do this if it's inside a list item context or similar? No, generally `{% endif %}` should be one tag.

fixed_content = re.sub(r'\{%\s*\n\s*endif\s*%\}', '{% endif %}', content)

# Also handle the case: `{% endif` ... `\n` ... `%}`
fixed_content = re.sub(r'\{%\s*endif\s*\n\s*%\}', '{% endif %}', fixed_content)

# Also handle: `{%` ... `\n` ... `endif %}`
fixed_content = re.sub(r'\{%\s*\n\s*endif\s*%\}', '{% endif %}', fixed_content)


if content != fixed_content:
    print("Fixed split tags using regex.")
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(fixed_content)
else:
    print("Regex didn't match. Trying manual block replacement.")
    # Fallback: We know the line numbers roughly (174-210).
    # We can just replace lines 174 to 210 with the clean blocks.
    # But line numbers might shift.
    
    # Let's find the index of "Nutritional Data (per 100g)"
    try:
        start_idx = -1
        for i, line in enumerate(lines):
            if "Nutritional Data (per 100g)" in line:
                start_idx = i - 1 # The div before it
                break
        
        if start_idx != -1:
            # We found the start. Now we need to find where the vitamins block ends.
            # It ends after the second </ul> and </div>
            
            # Let's just replace the next ~36 lines with our new content.
            # We need to be careful.
            
            # Let's verify the content of the lines we are about to replace.
            # We expect to see "Vitamins & Minerals" around line start_idx + 20
            
            # Construct the new content list
            new_lines = lines[:start_idx]
            new_lines.append(new_nutritional_block + '\n\n')
            new_lines.append(new_vitamins_block + '\n')
            
            # Where do we resume?
            # We need to find the line after the vitamins block.
            # The vitamins block ends with </div>.
            # In the original file, there is a </div> closing the row (line 211).
            
            # Let's look for "Data sourced from" which comes after.
            resume_idx = -1
            for i in range(start_idx, len(lines)):
                if "Data sourced from" in lines[i]:
                    resume_idx = i - 3 # There is a <div class="mt-3..."> before it, and a </div> before that.
                    # Actually, let's look for the <div class="mt-3 pt-3 border-top">
                    break
            
            if resume_idx == -1:
                 # Try finding the div with mt-3 pt-3
                 for i in range(start_idx, len(lines)):
                    if 'class="mt-3 pt-3 border-top"' in lines[i]:
                        resume_idx = i
                        break
            
            if resume_idx != -1:
                # We need to keep the </div> that closes the row?
                # The original structure:
                # <div class="row">
                #    <div class="col-md-6">...</div>
                #    <div class="col-md-6">...</div>
                # </div> <!-- This div is at line 211 -->
                # <div class="mt-3 ...">
                
                # So we should resume at resume_idx.
                # And we need to make sure we closed the row?
                # My new blocks are just the two cols. They don't include the row wrapper (which is outside).
                # Wait, looking at the file content:
                # 174: <div class="col-md-6"> ...
                # ...
                # 210: </div>
                # 211: </div> <!-- Closes row? -->
                
                # So I should replace from start_idx up to resume_idx (exclusive).
                # But wait, resume_idx is the <div class="mt-3...">.
                # The line before it is </div> (closing row?).
                # My new blocks do NOT include the closing row div.
                # So I should append the closing row div?
                
                # Let's just write the two blocks.
                # And we need to make sure we consume all the bad lines.
                
                # The bad lines are between start_idx and resume_idx.
                # If I replace lines[start_idx:resume_idx] with my new blocks, I might be missing the closing </div> for the row if it was inside that range?
                # In the file view:
                # 211: </div>
                # 213: <div class="mt-3 pt-3 border-top">
                
                # So resume_idx should be 213 (0-indexed? lines is list).
                # If I find "mt-3 pt-3 border-top", that is line 213.
                # I want to replace everything before it, starting from start_idx.
                # But I need to keep the closing </div> at 211?
                # Or is it part of the replacement?
                
                # My new blocks end with </div>.
                # The second block ends with </div>.
                # So I need one more </div> to close the row.
                
                new_lines.append('                                </div>\n') # Closing the row
                
                new_lines.extend(lines[resume_idx:])
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(new_lines)
                print("Manual block replacement applied.")
            else:
                print("Could not find resume point.")
        else:
            print("Could not find start point.")
    except Exception as e:
        print(f"Error during manual replacement: {e}")

