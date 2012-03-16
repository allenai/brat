#!/usr/bin/env python

# Script to convert a column-based BIO-formatted entity-tagged file
# into standoff with reference to the original text.

import sys
import re
import os
import codecs

class taggedEntity:
    def __init__(self, startOff, endOff, eType, idNum, fullText):
        self.startOff = startOff
        self.endOff   = endOff  
        self.eType    = eType   
        self.idNum    = idNum   
        self.fullText = fullText

        self.eText = fullText[startOff:endOff]

    def __str__(self):
        return "T%d\t%s %d %d\t%s" % (self.idNum, self.eType, self.startOff, self.endOff, self.eText)

    def check(self):
        # sanity checks: the string should not contain newlines and
        # should be minimal wrt surrounding whitespace
        assert "\n" not in self.eText, "ERROR: newline in entity: '%s'" % self.eText
        assert self.eText == self.eText.strip(), "ERROR: entity contains extra whitespace: '%s'" % self.eText

def BIO_to_standoff(BIOtext, reftext, tokenidx=2, tagidx=-1):
    BIOlines = BIOtext.split('\n')
    return BIO_lines_to_standoff(BIOlines, reftext, tokenidx, tagidx)

def BIO_lines_to_standoff(BIOlines, reftext, tokenidx=2, tagidx=-1):
    taggedTokens = []

    ri, bi = 0, 0
    while(ri < len(reftext)):
        if bi >= len(BIOlines):
            print >> sys.stderr, "Warning: received BIO didn't cover given text"
            break

        BIOline = BIOlines[bi]

        if re.match(r'^\s*$', BIOline):
            # the BIO has an empty line (sentence split); skip
            bi += 1
        else:
            # assume tagged token in BIO. Parse and verify
            fields = BIOline.split('\t')

            try:
                tokentext = fields[tokenidx]
            except:
                print >> sys.stderr, "Error: failed to get token text (field %d) on line: %s" % (tokenidx, BIOline)
                raise

            try:
                tag = fields[tagidx]
            except:
                print >> sys.stderr, "Error: failed to get token text (field %d) on line: %s" % (tagidx, BIOline)
                raise

            m = re.match(r'^([BIO])((?:-[A-Za-z0-9_-]+)?)$', tag)
            assert m, "ERROR: failed to parse tag '%s'" % tag
            ttag, ttype = m.groups()

            # strip off starting "-" from tagged type
            if len(ttype) > 0 and ttype[0] == "-":
                ttype = ttype[1:]

            # sanity check
            assert ((ttype == "" and ttag == "O") or
                    (ttype != "" and ttag in ("B","I"))), "Error: tag/type mismatch %s" % tag

            # go to the next token on reference; skip whitespace
            while ri < len(reftext) and reftext[ri].isspace():
                ri += 1

            # verify that the text matches the original
            assert reftext[ri:ri+len(tokentext)] == tokentext, "ERROR: text mismatch: reference '%s' tagged '%s'" % (reftext[ri:ri+len(tokentext)].encode("UTF-8"), tokentext.encode("UTF-8"))

            # store tagged token as (begin, end, tag, tagtype) tuple.
            taggedTokens.append((ri, ri+len(tokentext), ttag, ttype))
            
            # skip the processed token
            ri += len(tokentext)
            bi += 1

            # ... and skip whitespace on reference
            while ri < len(reftext) and reftext[ri].isspace():
                ri += 1
            
    # if the remaining part either the reference or the tagged
    # contains nonspace characters, something's wrong
    if (len([c for c in reftext[ri:] if not c.isspace()]) != 0 or
        len([c for c in BIOlines[bi:] if not re.match(r'^\s*$', c)]) != 0):
        assert False, "ERROR: failed alignment: '%s' remains in reference, '%s' in tagged" % (reftext[ri:], BIOlines[bi:])

    standoff_entities = []

    idIdx = 1
    prevTag, prevEnd = "O", 0
    currType, currStart = None, None
    for startoff, endoff, ttag, ttype in taggedTokens:

        if prevTag != "O" and ttag != "I":
            # previous entity does not continue into this tag; output
            assert currType is not None and currStart is not None, "ERROR in %s" % fn
            
            standoff_entities.append(taggedEntity(currStart, prevEnd, currType, idIdx, reftext))

            idIdx += 1

            # reset current entity
            currType, currStart = None, None

        elif prevTag != "O":
            # previous entity continues ; just check sanity
            assert ttag == "I", "ERROR in %s" % fn
            assert currType == ttype, "ERROR: entity of type '%s' continues as type '%s' in %s" % (currType, ttype, fn)
            
        if ttag == "B":
            # new entity starts
            currType, currStart = ttype, startoff
            
        prevTag, prevEnd = ttag, endoff

    # if there's an open entity after all tokens have been processed,
    # we need to output it separately
    if prevTag != "O":
        standoff_entities.append(taggedEntity(currStart, prevEnd, currType, idIdx, reftext))

    for e in standoff_entities:
        e.check()

    return standoff_entities

if __name__ == "__main__":
    print "Sorry, no CLI implemented yet (should be easy to do though)."
