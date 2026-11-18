from cves import captions as CAP

W = [[0.0, .3, "hello"], [.3, .6, "there."], [.7, 1.0, "this"], [1.0, 1.3, "is"], [1.3, 1.6, "a"], [1.6, 2.0, "longer"],
     [2.0, 2.4, "sentence"], [2.4, 2.8, "that"], [2.8, 3.2, "keeps"], [3.2, 3.6, "going"], [3.6, 4.0, "on."]]

def words(ev): return [w for _, _, ph in ev for w, _ in ph]

def test_never_crosses_a_sentence_end():
    ev = CAP.build(W, {"max_chars": 40, "case": "as_spoken"}, 5.0)
    for _, _, ph in ev[:-1]:
        assert not any(w.endswith(".") for w, _ in ph[:-1])
    assert words(ev) == [w for _, _, w in W]

def test_max_chars_and_one_word():
    ev = CAP.build(W, {"max_chars": 16}, 5.0)
    assert all(len(" ".join(w for w, _ in ph)) <= 16 or len(ph) == 1 for _, _, ph in ev)
    ev1 = CAP.build(W, {"style": "one_word"}, 5.0)
    assert all(len(ph) == 1 for _, _, ph in ev1)

def test_case_modes_and_fixes():
    up = CAP.build(W, {"case": "upper"}, 5.0); assert all(w.isupper() for w in words(up) if w.isalpha())
    sent = CAP.build(W, {"case": "sentence"}, 5.0); assert words(sent)[0] == "Hello" and words(sent)[2] == "This"
    fx = CAP.build(W, {"fixes": {"hello": "hi"}}, 5.0); assert words(fx)[0].lower() == "hi"

def test_events_are_ordered_and_cover_the_words():
    ev = CAP.build(W, {}, 5.0)
    assert all(a < b for a, b, _ in ev) and all(ev[i][1] <= ev[i + 1][0] + 1e-9 for i in range(len(ev) - 1))
    assert ev[-1][1] == 5.0
