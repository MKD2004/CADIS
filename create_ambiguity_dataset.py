import nltk
import csv
import random
from nltk.corpus import ppattach

try:
    nltk.data.find('corpora/ppattach')
except LookupError:
    nltk.download('ppattach', quiet=True)

nltk.download('ppattach', quiet=True)

def load_ppattach_data():
    data = []
    for t in ppattach.tuples(['training', 'devset', 'test']):
        data.append({
            'verb': t[1],
            'noun1': t[2],
            'prep': t[3],
            'noun2': t[4],
            'attachment': t[5]
        })
    return data

STOP_WORDS = {'is', 'was', 'are', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'to', 'the', 'a', 'an', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from', 'as', 'into', 'through', 'during', 'before', 'after', 'above', 'below', 'between', 'under', 'again', 'further', 'then', 'once', "'s", 's', 'given', 'got', 'seen', 'made', 'taken', 'put', 'let', 'got', 'run', 'began', 'began', 'become', 'came', 'came', 'fell', 'felt', 'found', 'got', 'kept', 'kept', 'left', 'meant', 'met', 'paid', 'paid', 'put', 'said', 'saw', 'saw', 'sent', 'set', 'shut', 'sold', 'sent', 'spent', 'stood', 'sung', 'sunk', 'slept', 'slept', 'swept', 'swept', 'swung', 'taught', 'told', 'thought', 'threw', 'understood', 'woke', 'wore', 'won', 'wrote', 'given', 'gotten', 'seen', 'taken', 'put', 'let', 'run', 'begun', 'become', 'come', 'fallen', 'felt', 'found', 'kept', 'left', 'meant', 'met', 'paid', 'said', 'saw', 'sent', 'set', 'shut', 'sold', 'spent', 'stood', 'sung', 'sunk', 'slept', 'swept', 'swung', 'taught', 'told', 'thought', 'threw', 'understood', 'woke', 'wore', 'won', 'wrote', 'getting', 'putting', 'letting', 'running', 'becoming', 'coming', 'falling', 'feeling', 'finding', 'keeping', 'leaving', 'meaning', 'meeting', 'paying', 'saying', 'seeing', 'sending', 'setting', 'shutting', 'selling', 'spending', 'standing', 'singing', 'sinking', 'sleeping', 'sweeping', 'swinging', 'teaching', 'telling', 'thinking', 'throwing', 'understanding', 'waking', 'wearing', 'winning', 'writing', 'making', 'giving'}

def is_valid_token(token):
    token = token.strip()
    if not token:
        return False
    if len(token) < 3:
        return False
    if token.replace('.', '').replace(',', '').replace("'", '').isdigit():
        return False
    if token.lower() in STOP_WORDS:
        return False
    return True

def reconstruct_sentence(verb, noun1, prep, noun2):
    templates = [
        f"The manager discussed the {noun2} with the {noun1} about the {verb} approach.",
        f"Users analyzed the {noun2} after the {verb} involving the {noun1}.",
        f"After the {verb}, the team reviewed the {noun2} concerning the {noun1}.",
        f"The {noun1} was examined in relation to the {noun2} during the {verb}.",
        f"Following the {verb}, the report covered the {noun2} linked to the {noun1}.",
        f"The {verb} process impacted the {noun1} regarding the {noun2}.",
        f"Analysis of the {noun2} revealed the {noun1} after the {verb}.",
        f"The {noun1} contributed to the {noun2} through the {verb} mechanism.",
    ]
    return random.choice(templates)

def main():
    raw_data = load_ppattach_data()
    
    filtered = []
    for item in raw_data:
        verb = item['verb'].lower().strip()
        noun1 = item['noun1'].lower().strip()
        prep = item['prep'].lower().strip()
        noun2 = item['noun2'].lower().strip()
        
        if all(is_valid_token(t) for t in [verb, noun1, noun2]):
            attachment = item['attachment'].strip().upper()
            if attachment in ('V', 'N'):
                true_head = 'verb' if attachment == 'V' else 'noun1'
                filtered.append({
                    'verb': verb,
                    'noun1': noun1,
                    'prep': prep,
                    'noun2': noun2,
                    'true_head': true_head
                })
    
    sampled = random.sample(filtered, min(100, len(filtered)))
    
    rows = []
    for item in sampled:
        sentence = reconstruct_sentence(item['verb'], item['noun1'], item['prep'], item['noun2'])
        rows.append({
            'sentence': sentence,
            'trigger_preposition': item['prep'],
            'candidate_1': item['verb'],
            'candidate_2': item['noun1'],
            'true_head': item['true_head']
        })
    
    with open('ambiguity_dataset.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['sentence', 'trigger_preposition', 'candidate_1', 'candidate_2', 'true_head'])
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"Exported {len(rows)} rows to ambiguity_dataset.csv")

if __name__ == '__main__':
    main()