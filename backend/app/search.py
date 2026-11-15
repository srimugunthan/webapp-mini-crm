"""Boolean search for the contacts list (decision 79).

Syntax (operators are UPPERCASE so ordinary words like "and" still search normally):
    a b            implicit AND
    a AND b        both
    a OR b         either
    NOT a  /  -a   exclude
    ( ... )        grouping
    "two words"    exact phrase
    field:term     restrict one term to name, company, position (alias title) or group
Precedence: NOT, then AND, then OR. Every term is a case-insensitive "contains" match.
The same language is used by the search, company, position and group boxes; each box has its own default field.
"""
import re

from .errors import AppError

MAX_LEN = 300
MAX_TERMS = 30
FIELDS = {"name": "name", "company": "company", "org": "company", "position": "position", "title": "position",
          "group": "group", "any": "any"}

_TOKEN = re.compile(r'\s*(?:(\()|(\))|"([^"]*)"|(\S+?)(?=\s|\(|\)|$))')


def _like(term: str) -> str:
    esc = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{esc}%"


def _tokenize(text: str):
    pos, out = 0, []
    text = text.strip()
    while pos < len(text):
        m = _TOKEN.match(text, pos)
        if not m or m.end() == pos:
            raise AppError(400, f"Search syntax error near “{text[pos:pos + 12]}”.")
        pos = m.end()
        if m.group(1):
            out.append(("(", None))
        elif m.group(2):
            out.append((")", None))
        elif m.group(3) is not None:
            out.append(("term", ("", m.group(3), True)))      # (field, text, quoted)
        else:
            word = m.group(4)
            if '"' in word:
                raise AppError(400, "Search syntax error: unclosed quote.")
            if word in ("AND", "OR", "NOT"):
                out.append((word, None))
            elif word in ("&&", "||"):
                out.append(("AND" if word == "&&" else "OR", None))
            elif word.startswith("-") and len(word) > 1:
                out.append(("NOT", None))
                out.append(_term_token(word[1:]))
            else:
                out.append(_term_token(word))
    return out


def _term_token(word: str):
    field = ""
    if ":" in word:
        head, _, rest = word.partition(":")
        if head.lower() in FIELDS and rest != "":
            field, word = FIELDS[head.lower()], rest
    return ("term", (field, word, False))


class _Parser:
    def __init__(self, tokens, default_field):
        self.t, self.i, self.default, self.terms = tokens, 0, default_field, 0

    def peek(self):
        return self.t[self.i][0] if self.i < len(self.t) else None

    def take(self):
        tok = self.t[self.i]
        self.i += 1
        return tok

    def parse(self):
        node = self.or_()
        if self.i != len(self.t):
            raise AppError(400, "Search syntax error: unexpected “)”.")
        return node

    def or_(self):
        node = self.and_()
        while self.peek() == "OR":
            self.take()
            node = ("or", node, self.and_())
        return node

    def and_(self):
        node = self.not_()
        while True:
            nxt = self.peek()
            if nxt == "AND":
                self.take()
                node = ("and", node, self.not_())
            elif nxt in ("term", "(", "NOT"):  # implicit AND
                node = ("and", node, self.not_())
            else:
                return node

    def not_(self):
        if self.peek() == "NOT":
            self.take()
            return ("not", self.not_())
        return self.atom()

    def atom(self):
        kind = self.peek()
        if kind == "(":
            self.take()
            node = self.or_()
            if self.peek() != ")":
                raise AppError(400, "Search syntax error: missing “)”.")
            self.take()
            return node
        if kind == "term":
            field, text, _quoted = self.take()[1]
            self.terms += 1
            if self.terms > MAX_TERMS:
                raise AppError(400, f"Search is too complex (more than {MAX_TERMS} terms).")
            if not text.strip():
                raise AppError(400, "Search syntax error: empty phrase.")
            return ("term", field or self.default, text)
        found = {None: "the end of the search", ")": "“)”", "AND": "AND", "OR": "OR"}.get(kind, str(kind))
        raise AppError(400, f"Search syntax error: expected a word but found {found}.")


def _term_sql(field: str, text: str):
    p = _like(text)
    if field == "name":
        return "(contacts.first_name || ' ' || contacts.last_name LIKE ? ESCAPE '\\')", [p]
    if field == "company":
        return "(contacts.company LIKE ? ESCAPE '\\')", [p]
    if field == "position":
        return "(contacts.position LIKE ? ESCAPE '\\')", [p]
    if field == "group":
        return ("EXISTS (SELECT 1 FROM group_members gm JOIN groups g ON g.id = gm.group_id"
                " WHERE gm.contact_id = contacts.id AND g.name LIKE ? ESCAPE '\\')"), [p]
    return ("(contacts.first_name || ' ' || contacts.last_name LIKE ? ESCAPE '\\' OR contacts.company LIKE ? ESCAPE '\\'"
            " OR contacts.position LIKE ? ESCAPE '\\')"), [p, p, p]


def _to_sql(node):
    kind = node[0]
    if kind == "term":
        return _term_sql(node[1], node[2])
    if kind == "not":
        sql, args = _to_sql(node[1])
        return f"NOT ({sql})", args
    ls, la = _to_sql(node[1])
    rs, ra = _to_sql(node[2])
    return f"({ls} {kind.upper()} {rs})", la + ra


def build(query: str | None, default_field: str = "any"):
    """Return (sql_condition, params) for a boolean query, or None when the query is empty."""
    if query is None or not query.strip():
        return None
    if len(query) > MAX_LEN:
        raise AppError(400, f"Search is too long (limit {MAX_LEN} characters).")
    tokens = _tokenize(query)
    if not tokens:
        return None
    return _to_sql(_Parser(tokens, default_field).parse())
