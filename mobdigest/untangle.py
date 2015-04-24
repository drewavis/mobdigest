"""
untangle.py

Untangle quoted text from "new context" in email messages.
"""

import re
import itertools

RE_CRLF = re.compile(r'\r\n|\r|\n')
RE_JUST_WS = re.compile(r'^\s*$')
RE_SINGLE_INTRO = re.compile(r'^on | wrote:$', re.IGNORECASE)
RE_REST_INTRO = re.compile(r'(^-----Original|^_____)', re.IGNORECASE)
RE_SIG_INTRO = re.compile('^--( =)?$|^_____+$|^sent (from|on) .+', re.IGNORECASE)

def untangle(text):
    """Untangle the text (including CRs/LFs) into a list of pairs.

    [('type', line)...]

    where possible types are:

    * ORIG:   What appears to be original content
    * INTRO:  "On 21 Oct 2012, Mike posited the following:"
    * BLANK:  Blank lines, still included in result
    * INLINE: Inline quoting, generally starting with ">" or "|"
    * BOTTOM: Bottom "original message" matter as a result of top-posting
    * SIG:    Sig and their introducers
    """

    result = []
    state = 'INIT'

    for line in RE_CRLF.split(text):

        if state in ['SIG', 'BOTTOM']:
            # nothing breaks us out of sig
            result.append((state, line))
            continue
        
        if RE_JUST_WS.match(line):
            result.append(('BLANK', line))
            continue

        line = line.strip()

        if line.startswith('>'):
            result.append(('QUOTE', line))
            continue

        if RE_SINGLE_INTRO.search(line):
            result.append(('INTRO', line))
            continue

        if RE_REST_INTRO.search(line):
            result.append(('INTRO', line))
            state = 'BOTTOM'
            continue

        if RE_SIG_INTRO.match(line):
            result.append(('SIG', line))
            state = 'SIG'
            continue

        # deal with broken quoted-printable encoding
        if result and result[-1][0] == 'QUOTE' and result[-1][1].endswith('='):
            result.append(('QUOTE', line))
            continue

        result.append(('ORIG', line))

    return result

def original_text_line_qty(untangled):
    """Return number of original text lines."""
    return len([tag for tag, line in untangled if tag == 'ORIG'])

def original_text(untangled, group='ORIG'):
    """Attempt to return a list paragraphs of original text from the
    email. Paragraphs are things that are separated by BLANKs."""
    
    result = []
    for grouping, line_group in itertools.groupby(
        untangled, 
        lambda pair: pair[0]):
        if grouping == group:
            result.append(' '.join(pair[1] for pair in line_group))
    return result

def fingerprint(untangled):
    """Return a "fingerprint" of the lines in this message, like:
    15:I1:B1:O3:S10."""
    result = []
    for grouping, line_group in itertools.groupby(
        untangled, 
        lambda pair: pair[0]):
        group_len = len(list(line_group))
        result.append('%s%d' % (grouping[0], group_len))
    return ':'.join(result)

def print_fmt(untangled):
    print 'fingerprint:', fingerprint(untangled)
    for tup in untangled:
        print '%10s %s' % tup

        
"""
Cases to fix:

---

      ORIG both the rheostat and motor were really hot. I'm thinking i may just run it
     INTRO on a timer (since i already have one) with the silicone mat. so 1/2 hour on
      ORIG and 1/2 hour off.

---

    QUOTE > > > >>>> > >
    QUOTE > > > >>>> > >> How about a thin-ish sheet of styrofoam between the plate a=
      ORIG nd
    QUOTE > the

"""
