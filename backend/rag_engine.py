import re
import math
from typing import List, Dict, Set

# Standard list of English stopwords to improve BM25 matching
STOPWORDS: Set[str] = {
    'a', 'about', 'above', 'after', 'again', 'against', 'all', 'am', 'an', 'and', 'any', 'are', 'arent', 'as', 'at',
    'be', 'because', 'been', 'before', 'being', 'below', 'between', 'both', 'but', 'by', 'cant', 'cannot', 'could',
    'couldnt', 'did', 'didnt', 'do', 'does', 'doesnt', 'doing', 'dont', 'down', 'during', 'each', 'few', 'for', 'from',
    'further', 'had', 'hadnt', 'has', 'hasnt', 'have', 'havent', 'having', 'he', 'hed', 'hell', 'hes', 'her', 'here',
    'heres', 'hers', 'herself', 'him', 'himself', 'his', 'how', 'hows', 'i', 'id', 'ill', 'im', 'ive', 'if', 'in',
    'into', 'is', 'isnt', 'it', 'its', 'itself', 'lets', 'me', 'more', 'most', 'mustnt', 'my', 'myself', 'no', 'nor',
    'not', 'of', 'off', 'on', 'once', 'only', 'or', 'other', 'ought', 'our', 'ours', 'ourselves', 'out', 'over', 'own',
    'same', 'shant', 'she', 'shed', 'shell', 'shes', 'should', 'shouldnt', 'so', 'some', 'such', 'than', 'that', 'thats',
    'the', 'their', 'theirs', 'them', 'themselves', 'then', 'there', 'theres', 'these', 'they', 'theyd', 'theyll',
    'theyre', 'theyve', 'this', 'those', 'through', 'to', 'too', 'under', 'until', 'up', 'very', 'was', 'wasnt', 'we',
    'wed', 'well', 'were', 'weve', 'werent', 'what', 'whats', 'when', 'whens', 'where', 'wheres', 'which', 'while',
    'who', 'whos', 'whom', 'why', 'whys', 'with', 'wont', 'would', 'wouldnt', 'you', 'youd', 'youll', 'youre', 'youve',
    'your', 'yours', 'yourself', 'yourselves'
}

def tokenize(text: str) -> List[str]:
    """Lowercase text and split by non-alphanumeric characters, filtering stopwords."""
    words = re.findall(r'\b\w+\b', text.lower())
    return [w for w in words if w not in STOPWORDS]

def chunk_text(text: str, chunk_size: int = 800, overlap: int = 150) -> List[str]:
    """
    Intelligently splits long text into overlapping chunks,
    respecting sentence/paragraph boundaries where possible.
    """
    # First, split into paragraphs
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    chunks = []
    
    current_chunk = []
    current_length = 0
    
    for paragraph in paragraphs:
        if len(paragraph) > chunk_size:
            sentences = re.split(r'(?<=[.!?])\s+', paragraph)
            for sentence in sentences:
                sentence_len = len(sentence)
                if current_length + sentence_len > chunk_size:
                    if current_chunk:
                        chunks.append(" ".join(current_chunk))
                    if len(current_chunk) > 1:
                        current_chunk = [current_chunk[-1], sentence]
                        current_length = len(current_chunk[0]) + 1 + sentence_len
                    else:
                        current_chunk = [sentence]
                        current_length = sentence_len
                else:
                    current_chunk.append(sentence)
                    current_length += (1 if current_length > 0 else 0) + sentence_len
        else:
            para_len = len(paragraph)
            if current_length + para_len > chunk_size:
                if current_chunk:
                    chunks.append("\n\n".join(current_chunk))
                current_chunk = [paragraph]
                current_length = para_len
            else:
                current_chunk.append(paragraph)
                current_length += (2 if current_length > 0 else 0) + para_len
                
    if current_chunk:
        chunks.append("\n\n".join(current_chunk))
        
    return chunks

class BM25Retriever:
    """Pure-Python BM25 Document Scorer & Retriever."""
    def __init__(self, corpus: List[str], k1: float = 1.5, b: float = 0.75):
        self.corpus = corpus
        self.k1 = k1
        self.b = b
        self.corpus_size = len(corpus)
        
        # Tokenize corpus
        self.tokenized_corpus = [tokenize(doc) for doc in corpus]
        
        # Calculate doc lengths and average length
        self.doc_lengths = [len(doc) for doc in self.tokenized_corpus]
        self.avg_doc_length = sum(self.doc_lengths) / max(1, self.corpus_size)
        
        # Term counts across corpus to calculate IDF
        self.doc_freqs: Dict[str, int] = {}
        # Term frequencies per document
        self.term_freqs: List[Dict[str, int]] = []
        
        for doc in self.tokenized_corpus:
            frequencies: Dict[str, int] = {}
            for term in doc:
                frequencies[term] = frequencies.get(term, 0) + 1
            self.term_freqs.append(frequencies)
            
            for term in frequencies.keys():
                self.doc_freqs[term] = self.doc_freqs.get(term, 0) + 1
                
        # Cache IDFs
        self.idf: Dict[str, float] = {}
        for term, freq in self.doc_freqs.items():
            self.idf[term] = math.log((self.corpus_size - freq + 0.5) / (freq + 0.5) + 1.0)
            
    def retrieve(self, query: str, top_n: int = 5) -> List[tuple[str, float]]:
        """Scores documents against the query and returns top_n chunks with scores."""
        query_tokens = tokenize(query)
        if not query_tokens:
            return [(doc, 0.0) for doc in self.corpus[:top_n]]
            
        scores = []
        for i in range(self.corpus_size):
            score = 0.0
            doc_len = self.doc_lengths[i]
            tf_dict = self.term_freqs[i]
            
            for token in query_tokens:
                if token in tf_dict:
                    tf = tf_dict[token]
                    idf_val = self.idf.get(token, 0.0)
                    numerator = tf * (self.k1 + 1.0)
                    denominator = tf + self.k1 * (1.0 - self.b + self.b * (doc_len / self.avg_doc_length))
                    score += idf_val * (numerator / denominator)
            scores.append((self.corpus[i], score))
            
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_n]
