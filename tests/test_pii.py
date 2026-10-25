from app.guardrails.pii import mask_pii


def test_email_masked():
    res = mask_pii("пишите на test.user@example.com")
    assert "<EMAIL>" in res.text
    assert res.found.get("email") == 1


def test_phone_masked():
    res = mask_pii("звоните +7 (999) 123-45-67")
    assert "<PHONE>" in res.text


def test_name_masked():
    res = mask_pii("Меня зовут Иван Петров, учусь в школе")
    assert "<NAME>" in res.text


def test_school_and_class_masked():
    res = mask_pii("Учусь в школе №123 в 10 классе")
    assert "<SCHOOL>" in res.text
    assert "<CLASS>" in res.text


def test_clean_text_unchanged():
    text = "Как подготовиться к ЕГЭ по математике"
    res = mask_pii(text)
    assert res.text == text
    assert not res.masked_anything