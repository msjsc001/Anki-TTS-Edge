import difflib
import re
import html
import math

class AlignmentEngine:
    def __init__(self):
        pass

    def align(self, original_text, tts_word_boundaries):
        """
        Aligns original text with TTS word boundaries using global sequence alignment.
        
        Args:
            original_text (str): The user input text.
            tts_word_boundaries (list): List of dicts from edge_tts.
                Each dict must have: {'text': str, 'offset': int, 'duration': int}
                (offset/duration are in 100ns units, usually converted to ms before here, 
                 but we expect raw or ms. Let's assume input has 'start_ms', 'end_ms' or we calculate it)
        
        Returns:
            dict: {
                "words": [
                    # Precise mapping of text segments to audio time
                    {'text': 'segment', 'start_char': 0, 'end_char': 5, 'start_ms': 100, 'end_ms': 500, 'word_idx': 0},
                    ...
                ],
                "sentences": [
                    # Precise sentence timings
                    {'text': 'Full sent.', 'start_char': 0, 'end_char': 20, 'start_ms': 100, 'end_ms': 5000}
                ]
            }
        """
        
        # 1. Prepare Sequence B (TTS String) and Map
        # We join all TTS words to form one long "spoken string" (B)
        # b_to_word_idx[j] tells us which word index the character B[j] belongs to.
        tts_text_builder = []
        b_to_word_idx = []
        
        # Ensure we have ms timings
        clean_boundaries = []
        
        for idx, wb in enumerate(tts_word_boundaries):
            # Normalize: unescape HTML entities to match what difflib sees in original text (if unescaped)
            # But wait, original_text is the source of truth.
            # If original has "&", and TTS returns "&", we want match.
            # If original has "&", and TTS returns "&amp;", we definitely want unescape.
            # So always unescape TTS text.
            w_text = html.unescape(wb.get("text", "")).strip()
            
            # Skip empty words
            if not w_text: 
                continue
                
            # Handle timing normalization if needed
            if "start_ms" not in wb:
                # Assume raw edge_tts units (100ns)
                start_ms = wb["offset"] / 10000
                duration_ms = wb["duration"] / 10000
                end_ms = start_ms + duration_ms
            else:
                start_ms = wb["start_ms"]
                end_ms = wb["end_ms"]
            
            clean_wb = wb.copy()
            clean_wb["cleaned_text"] = w_text
            clean_wb["start_ms"] = start_ms
            clean_wb["end_ms"] = end_ms
            clean_boundaries.append(clean_wb)
            
            # Build sequence B
            tts_text_builder.append(w_text)
            for _ in w_text:
                b_to_word_idx.append(len(clean_boundaries) - 1)
        
        sequence_b = "".join(tts_text_builder).lower()
        sequence_a = original_text.lower()
        
        # 2. Global Alignment (Diff)
        matcher = difflib.SequenceMatcher(None, sequence_a, sequence_b)
        
        # char_map[i] = word_index (in clean_boundaries)
        # Initialize with -1 (unmapped/silence)
        char_map = [-1] * len(original_text)
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                # Direct match: A[i] maps to B[j] -> word_idx
                for k in range(i2 - i1):
                    # Safety check
                    if j1 + k < len(b_to_word_idx):
                        char_map[i1 + k] = b_to_word_idx[j1 + k]
            
            elif tag == 'replace':
                # Mismatch (e.g. "1" -> "one")
                # Distribute A[i1:i2] across words covered by B[j1:j2]
                a_len = i2 - i1
                b_len = j2 - j1
                
                if b_len > 0:
                     for k in range(a_len):
                        # Map relative position in A block to relative position in B block
                        # Linear interpolation
                        rel_b = math.floor(k * b_len / a_len)
                        if j1 + rel_b < len(b_to_word_idx):
                             char_map[i1 + k] = b_to_word_idx[j1 + rel_b]
            
            # 'delete': A has text but B doesn't (silence/skipped). Leave as -1.
            # 'insert': B has text but A doesn't (hallucination?). Ignore.
            
        # 3. Consolidate Character Mapping into Word Segments
        aligned_words = []
        
        current_word_idx = -1
        current_start = -1
        
        for i, w_idx in enumerate(char_map):
            if w_idx != current_word_idx:
                # Close previous segment
                if current_word_idx != -1:
                    wb = clean_boundaries[current_word_idx]
                    aligned_words.append({
                        "text": original_text[current_start:i],
                        "start_char": current_start,
                        "end_char": i,
                        "start_ms": wb["start_ms"],
                        "end_ms": wb["end_ms"],
                        "word_idx": len(aligned_words) # Sequential index for UI
                    })
                
                # Start new segment
                if w_idx != -1:
                    current_start = i
                current_word_idx = w_idx
        
        # Close last segment
        if current_word_idx != -1:
            wb = clean_boundaries[current_word_idx]
            aligned_words.append({
                "text": original_text[current_start:len(original_text)],
                "start_char": current_start,
                "end_char": len(original_text),
                "start_ms": wb["start_ms"],
                "end_ms": wb["end_ms"],
                "word_idx": len(aligned_words)
            })
            
        # 4. Sentence Segmentation & Timing
        sentences = self._segment_sentences(original_text)
        aligned_sentences = []
        
        for sent in sentences:
            # Find time range covered by this sentence
            s_start = sent["start_char"]
            s_end = sent["end_char"]
            
            min_ms = float('inf')
            max_ms = 0
            found_words = False
            
            # Look for words overlapping with this sentence
            for w in aligned_words:
                # Check overlap
                if w["start_char"] < s_end and w["end_char"] > s_start:
                    min_ms = min(min_ms, w["start_ms"])
                    max_ms = max(max_ms, w["end_ms"])
                    found_words = True
            
            if found_words:
                sent["start_ms"] = min_ms
                sent["end_ms"] = max_ms
                aligned_sentences.append(sent)
        
        return {
            "words": aligned_words,
            "sentences": aligned_sentences
        }

    def _segment_sentences(self, text):
        """
        Segment text into logical sentences using Regex.
        Same logic as original but decoupled.
        """
        sentences = []
        # Support Chinese/English/Japanese punctuation
        # (.) (?!) (!?) (...) (。) (！) (？) (……)
        # Lookbehind not needed if we split keeping delimiters
        
        pattern = r'([。！？；!?;.…]+)'
        
        start = 0
        for match in re.finditer(pattern, text):
            end = match.end()
            # Everything from start to end of punctuation is a chunk
            chunk = text[start:end].strip()
            if chunk:
                sentences.append({
                    "text": chunk,
                    "start_char": start, # Approximate (trimmed)
                    "end_char": end      # This is raw end
                })
            start = end
            
        # Remaining
        if start < len(text):
            chunk = text[start:].strip()
            if chunk:
                sentences.append({
                    "text": chunk,
                    "start_char": start,
                    "end_char": len(text)
                })
                
        # Refine start_char (because we stripped)
        # Actually proper way:
        refined_sentences = []
        
        # Using the split method from original code which was decent
        # But let's write a robust iterator
        
        current_pos = 0
        current_text = ""
        sentence_start = 0
        
        # Re-implementing a simpler robust scan
        # We walk char by char? No, too slow for huge text? 
        # But text is usually < 5000 chars for TTS.
        
        # Let's use the finditer approach strictly
        # We define a sentence as: Content + Punctuation
        
        # Split by punctuation, keep delimiter
        parts = re.split(f'({pattern})', text) 
        # re.split with groups returns [text, delimiter, text, delimiter...]
        # Wait, pattern inside pattern in split?
        # r'([。！？...]+)' is capturing group.
        
        # Let's iterate and merge
        buffer_text = ""
        buffer_start = 0
        
        # Actually the original parse_sentences was okay, let's adapt it to be cleaner
        # Iterate matches of Sentences
        
        # Regex for "Non-punctuation followed by optional punctuation"
        # [^Punc]+ [Punc]*
        
        iter_pattern = r'[^。！？；!?;.…]+[。！？；!?;.…]*'
        
        for match in re.finditer(iter_pattern, text):
            full_span = match.group()
            # Skip pure whitespace matches if any
            if not full_span.strip():
                continue
                
            refined_sentences.append({
                "text": full_span, # raw text including newline/space
                "start_char": match.start(),
                "end_char": match.end()
            })
            
        return refined_sentences
