"""Simple recursive descent expression parser."""


class ParseError(Exception):
    pass


class Lexer:
    def __init__(self, text: str):
        self.text = text
        self.pos = 0

    def skip_whitespace(self):
        while self.pos < len(self.text) and self.text[self.pos].isspace():
            self.pos += 1

    def next_token(self):
        self.skip_whitespace()
        if self.pos >= len(self.text):
            return None, None
        ch = self.text[self.pos]
        if ch.isdigit():
            start = self.pos
            while self.pos < len(self.text) and self.text[self.pos].isdigit():
                self.pos += 1
            return "NUM", int(self.text[start : self.pos])
        if ch in "+-*/()":
            self.pos += 1
            return ch, ch
        raise ParseError(f"Unexpected character: {ch!r} at position {self.pos}")

    def peek(self):
        saved = self.pos
        tok, val = self.next_token()
        self.pos = saved
        return tok, val


class Parser:
    def __init__(self, text: str):
        self.lexer = Lexer(text)

    def parse(self) -> int:
        result = self.expr()
        tok, _ = self.lexer.next_token()
        if tok is not None:
            raise ParseError("Unexpected token after expression")
        return result

    def expr(self) -> int:
        left = self.term()
        while True:
            tok, _ = self.lexer.peek()
            if tok == "+":
                self.lexer.next_token()
                left += self.term()
            elif tok == "-":
                self.lexer.next_token()
                left -= self.term()
            else:
                break
        return left

    def term(self) -> int:
        left = self.factor()
        while True:
            tok, _ = self.lexer.peek()
            if tok == "*":
                self.lexer.next_token()
                left *= self.factor()
            elif tok == "/":
                self.lexer.next_token()
                right = self.factor()
                if right == 0:
                    raise ParseError("Division by zero")
                left //= right
            else:
                break
        return left

    def factor(self) -> int:
        tok, val = self.lexer.peek()
        if tok == "NUM":
            self.lexer.next_token()
            return val
        if tok == "-":
            self.lexer.next_token()
            return -self.factor()
        if tok == "(":
            self.lexer.next_token()
            result = self.expr()
            tok, _ = self.lexer.next_token()
            if tok != ")":
                raise ParseError("Expected ')'")
            return result
        raise ParseError(f"Unexpected token: {tok!r}")


def evaluate(expression: str) -> int:
    return Parser(expression).parse()
