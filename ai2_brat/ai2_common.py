#!/usr/bin/env python3
# 0-*- Mode: Python; tab-width: 4; indent-tabs-mode: nil; coding: utf-8; -*-

import sys
import os.path
import itertools
import glob
import re
import codecs
import logging
import en_core_web_md

if "." in __name__:
    from . import annotation
else:
    import annotation


class EnhancedAnnotatedDoc:
    """A wrapper for a brat annotation.TextAnnotation.

    Indices into the doc and spans are measured in tokens.

    """
    NLP = None

    def __init__(self, brat_annotation):
        EnhancedAnnotatedDoc._init_nlp()
        self.document_id = os.path.basename(brat_annotation.get_document())
        self.annotator_id = os.path.basename(os.path.dirname(brat_annotation.get_document()))
        self.document_text = brat_annotation.get_document_text()
        self.char_len = len(self.document_text)
        self.spacy_doc = EnhancedAnnotatedDoc.NLP(self.document_text)
        self.brat_annotation = brat_annotation
        self.entities = [Entity(e, self) for e in self.brat_annotation.get_entities()]
        self.relations = [Relation(r, self) for r in self.brat_annotation.get_relations()]

    def get_entities(self):
        return self.entities

    def __getitem__(self, key):
        return self.spacy_doc.__getitem__(key)

    def __len__(self):
        return self.spacy_doc.__len__()

    def get_entity(self, id):
        entity = next((e for e in self.entities if e.id == id), None)
        return entity

    def remove_entity(self, entity, force_remove_relations=False):
        relations = entity.get_relations()
        if not force_remove_relations and relations:
            ValueError("Entity {} has relations and will not be removed.".format(entity))
        for r in relations:
            self.remove_relation(r)
        self.entities = [e for e in self.entities if e != entity]
        self.brat_annotation.del_annotation(entity.brat_annotation)

    def remove_relation(self, relation):
        self.relations = [r for r in self.relations if r != relation]
        self.brat_annotation.del_annotation(relation.brat_annotation)

    @staticmethod
    def _init_nlp():
        if EnhancedAnnotatedDoc.NLP is None:
            EnhancedAnnotatedDoc.NLP = en_core_web_md.load()

    def write_to_path(self, path):
        """Write .txt and .ann files representing the underlying brat annotation.
        'path' is expected to be a directory.
        """
        if not os.path.isdir(path):
            raise ValueError("{} is not a directory".format(path))

        with codecs.open(os.path.join(path, self.document_id + ".txt"), mode="w", encoding="utf-8") as txt:
            txt.write(self.brat_annotation.get_document_text())
        with codecs.open(os.path.join(path, self.document_id + ".ann"), mode="w", encoding="utf-8") as ann:
            ann.write(str(self.brat_annotation))


class Entity:
    """Wrapper for brat annotation. Spans are in tokens."""
    def __init__(self, brat_annotation, parent_doc):
        self.brat_annotation = brat_annotation
        self.parent_doc = parent_doc
        self.id = brat_annotation.id
        self.type = brat_annotation.type
        spans = [match_span_to_tokens(parent_doc, span) for span in brat_annotation.spans]
        self.set_spans(spans)

    def same_span(self, other):
        return set(self.character_spans) == set(other.character_spans)

    def overlaps(self, other):
        return any_overlapping_spans(self.brat_annotation, other.brat_annotation)

    def get_relations(self):
        return [r for r in self.parent_doc.relations if r.arg1 == self or r.arg2 == self]

    def __len__(self):
        return sum((span[1] - span[0] for span in self.spans))

    def set_spans(self, spans):
        self.character_spans = []
        self.spans = spans
        for span in spans:
            l = self.parent_doc[span[0]].idx
            last_token = self.parent_doc[span[1] - 1]
            r = last_token.idx + len(last_token)
            self.character_spans.append((l, r))
        self.brat_annotation.spans = self.character_spans
        doc_text = self.parent_doc.document_text
        new = " ".join((doc_text[span[0]:span[1]] for span in self.character_spans))
        self.brat_annotation.text = new

    def __str__(self):
        # TODO: something nicer?
        return self.brat_annotation.__str__()

    def get_tokens(self):
        return itertools.chain.from_iterable(
            (self.parent_doc[i] for i in range(span[0], span[1]))
            for span in self.spans)


class Relation:
    def __init__(self, brat_annotation, parent_doc):
        self.brat_annotation = brat_annotation
        self.parent_doc = parent_doc
        self.type = brat_annotation.type
        self.arg1 = parent_doc.get_entity(brat_annotation.arg1)
        self.arg2 = parent_doc.get_entity(brat_annotation.arg2)
        assert self.arg1 is not None
        assert self.arg2 is not None

    def swap(self, a, b):
        """Swap a for b in this relation"""
        if self.arg1 == a:
            self.arg1 = b
            self.brat_annotation.arg1 = b.id
        elif self.arg2 == a:
            self.arg2 = b
            self.brat_annotation.arg2 = b.id
        else:
            raise ValueError("Entity {} is not a part of relation {}".format(a, self))

    def get_comments(self):
        return [c for c in self.parent_doc.brat_annotation.get_oneline_comments()
                if c.target == self.brat_annotation.id]


def get_identifiers(*paths):
    found_identifiers = []
    extensions = re.compile(r"\.(txt|ann)$")
    for path in paths:
        if os.path.isdir(path):
            # Don't recur, just check one level down
            children = [f for f in glob.glob(os.path.join(path, "*")) if extensions.search(f)]
            if not children:
                logging.warn("No annotation files found in {}\n".format(path))
            identifiers = [child[:-4] for child in children]
            found_identifiers += list(set(identifiers))
        else:
            if extensions.search(path):
                found_identifiers.append(path[:-4])
            else:
                found_identifiers.append(path)
    return found_identifiers


def get_docs(*paths):
    return [load_doc(i) for i in get_identifiers(*paths)]


def load_doc(identifier):
    """An identifier is the path to a pair of a .ann file and a .txt file, minus
    the extension for either.

    """
    try:
        return EnhancedAnnotatedDoc(annotation.TextAnnotations(identifier))
    except AssertionError as e:
        sys.stderr.write("Failed to load doc {} with error {}\n".format(identifier, e))


def match_span_to_tokens(doc, span):
    """Converts a character span to a token span.

    The token span will cover any token that is touched by the character span.

    """
    loff = span[0]
    roff = span[1]
    leftToken = get_token_starting_at_char_offset(doc, loff)
    if leftToken is None:
        leftToken = get_token_at_char_offset(doc, loff)
        # The below block could trigger if whitespace on the left side of a token were annotated
        if leftToken is None:
            for i in range(len(doc)):
                if doc[i].idx > loff:
                    l = i
                    break
        else:
            l = leftToken.i
    else:
        l = leftToken.i

    rightToken = get_token_at_char_offset(doc, roff)
    # Here a `None' result means there is nothing to correct
    if rightToken is not None and rightToken.idx < roff:
        r = rightToken.i + 1
    elif rightToken is not None and rightToken.idx == roff:
        r = rightToken.i
    else:
        for i in range(len(doc)):
            if doc[i].idx > roff:
                r = i
                break

    # The maximum distance in characters to move a span without complaining
    MAXIMUM_CORRECTION = 3
    move = max(abs(doc[l].idx - loff), abs((doc[r - 1].idx + len(doc[r - 1])) - roff))
    if move > MAXIMUM_CORRECTION:
        logging.warn("In fitting span {} to tokens in doc {}, had to move {} characters"
                     .format(span, doc.document_id, move))

    return (l, r)


def get_token_starting_at_char_offset(doc, offset):
    at = get_token_at_char_offset(doc, offset)
    if at.idx == offset:
        return at
    else:
        return None


def get_token_at_char_offset(doc, offset):
    l = 0
    r = len(doc)
    while r - l > 1:
        mid = (l + r) // 2
        if doc[mid].idx > offset:
            r = mid
        else:
            l = mid

    if doc[l].idx + len(doc[l]) > offset:
        return doc[l]
    else:
        return None


def get_token_ending_at_char_offset(doc, offset):
    l = 0
    r = len(doc)
    while r - l > 1:
        mid = (l + r) // 2
        if doc[mid].idx + len(doc[mid]) > offset:
            r = mid
        else:
            l = mid

    if doc[l].idx + len(doc[l]) == offset:
        return doc[l]
    else:
        return None


def find_overlapping(doc):
    """Finds pairs of entities which overlap in 'doc'."""
    return [c for c in itertools.combinations(doc.get_entities(), 2)
            if any_overlapping_spans(c[0], c[1])]


def any_overlapping_spans(a, b):
        for i in a.spans:
            for j in b.spans:
                if j[0] < i[1] and i[0] < j[1]:
                    return True
        return False


# Requires the spans be independent
def spans_to_biluo(spans, total_len):
    # o -> 0, b -> 1, i -> 2, l -> 3, u -> 4
    spans = sorted(spans)
    result = [0] * total_len
    i = 0
    j = 0
    while j < len(spans):
        if i < spans[j][0]:  # o
            result[i] = 0
        elif i == spans[j][0] and (i + 1 < spans[j][1]):  # b
            result[i] = 1
        elif i == spans[j][0]:  # u
            result[i] = 4
            j += 1
        elif i + 1 == spans[j][1]:  # l
            result[i] = 3
            j += 1
        else:  # i
            result[i] = 2
        i += 1
    return result
