import re

REF_RE = re.compile('%[a-z0-9_]*')

# TODO: It would be nice to require that grammars aren't ambiguous (by
# being very conservative about the grammars we accept). I haven't
# quite thought through how to do this.

class Rule(object):
    def __init__(self, children, bits, mybits):
        self.children = children
        self.bits = bits
        self.mybits = mybits

    def __repr__(self):
        return "(%r, %r, %r)" % (self.children, self.bits, self.mybits)

def log2(n):
    if n == 1:
        return 0
    if n % 2 == 0:
        return 1 + log2(n / 2)
    raise RuntimeError("%d is not a power of 2" % (n, ))

class Ptree(object):
    """A grammar for parsing and generating passphrases."""
    def __init__(self, datafile):
        self.rules = {}

        for line in datafile.readlines():
            line = line.split('#')[0].strip()
            if not line:
                continue

            term, rhs = line.split(' = ')
            expansions = rhs.split(' | ')
            children = []
            for expansion in expansions:
                refs = [ref[1:] for ref in re.findall(REF_RE, expansion)]
                pieces = re.split(REF_RE, expansion)
                children.append((refs, pieces))
            mybits = log2(len(expansions))
            self.rules[term] = Rule(children, 0, mybits)

        def setbits(nodename):
            node = self.rules[nodename]
            if node.bits > 0:
                return node.bits
            if node.bits == 0:
                node.bits = -1
                bits = [sum(setbits(ref) for ref in refs)
                        for refs, pieces in node.children]
                assert len(set(bits)) == 1
                node.bits = bits[0] + node.mybits
                return node.bits
            raise ValueError("Cycle detected for node %s" % (nodename, ))

        self.bits = setbits('root')

    def generate(self, r):
        def genhelper(node, r, offset):
            offset -= node.mybits
            choice = r >> offset
            r &= (2 ** offset - 1)
            refs, pieces = node.children[choice]
            ipieces = iter(pieces)
            ret = ipieces.next()
            for ref in refs:
                retd, r, offset = genhelper(self.rules[ref], r, offset)
                ret += retd + ipieces.next()
            return ret, r, offset

        return genhelper(self.rules['root'], r, self.rules['root'].bits)[0]

    def parse(self, s):
        class NoMatch(Exception):
            pass

        def parsehelper(node, s, r):
            for i in xrange(len(node.children)):
                refs, pieces = node.children[i]
                # Note that len(refs) + 1 == len(pieces)
                irefs = iter(refs)
                try:
                    my_s = s
                    for piece in pieces:
                        if my_s.startswith(piece):
                            my_s = my_s[len(piece):]
                            try:
                                ref = irefs.next()
                            except StopIteration:
                                return my_s, (r << node.mybits) + i
                            my_s, r = parsehelper(self.rules[ref],
                                                  my_s, r)
                        else:
                            raise NoMatch()
                    break
                except NoMatch:
                    continue
            else:
                raise NoMatch()

        unparsed, r = parsehelper(self.rules['root'], s, 0)
        assert unparsed == ''
        return r
