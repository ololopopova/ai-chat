"""Unit тесты для HTMLParser."""

from src.services.ingest.html_parser import HTMLParser


class TestHTMLParser:
    """Тесты для HTMLParser."""

    def test_parse_single_h1_section(self) -> None:
        """Парсинг документа с одним H1."""
        html = """
        <html>
        <body>
            <h1>Заголовок 1</h1>
            <p>Первый параграф</p>
            <p>Второй параграф</p>
        </body>
        </html>
        """

        parser = HTMLParser()
        sections = parser.parse(html)

        assert len(sections) == 1
        assert sections[0].header == "Заголовок 1"
        assert sections[0].header_level == 1
        assert "Первый параграф" in sections[0].content
        assert "Второй параграф" in sections[0].content

    def test_parse_multiple_h1_sections(self) -> None:
        """Парсинг документа с несколькими H1."""
        html = """
        <html>
        <body>
            <h1>Секция 1</h1>
            <p>Контент секции 1</p>
            <h1>Секция 2</h1>
            <p>Контент секции 2</p>
            <h1>Секция 3</h1>
            <p>Контент секции 3</p>
        </body>
        </html>
        """

        parser = HTMLParser()
        sections = parser.parse(html)

        assert len(sections) == 3
        assert sections[0].header == "Секция 1"
        assert "Контент секции 1" in sections[0].content
        assert sections[1].header == "Секция 2"
        assert "Контент секции 2" in sections[1].content
        assert sections[2].header == "Секция 3"
        assert "Контент секции 3" in sections[2].content

    def test_parse_no_h1_headers(self) -> None:
        """Парсинг документа без H1 — весь документ одна секция."""
        html = """
        <html>
        <body>
            <p>Просто текст без заголовков</p>
            <p>Ещё текст</p>
        </body>
        </html>
        """

        parser = HTMLParser()
        sections = parser.parse(html)

        assert len(sections) == 1
        assert sections[0].header == "Document"
        assert "Просто текст без заголовков" in sections[0].content

    def test_parse_table(self) -> None:
        """Парсинг таблицы в текст."""
        html = """
        <html>
        <body>
            <h1>Таблица добавок</h1>
            <table>
                <tr>
                    <td>Добавка</td>
                    <td>Совместимость</td>
                    <td>Комментарий</td>
                </tr>
                <tr>
                    <td>Ежовик</td>
                    <td>✅ Совместимо</td>
                    <td>Поддержка нервной системы</td>
                </tr>
                <tr>
                    <td>Мелатонин</td>
                    <td>⚠️ Осторожно</td>
                    <td>Принимать перед сном</td>
                </tr>
            </table>
        </body>
        </html>
        """

        parser = HTMLParser()
        sections = parser.parse(html)

        assert len(sections) == 1
        content = sections[0].content

        # Проверить, что таблица преобразована в структурированный текст
        assert "Добавка: Ежовик" in content
        assert "Совместимость: ✅ Совместимо" in content
        assert "Комментарий: Поддержка нервной системы" in content
        assert "Добавка: Мелатонин" in content
        assert "---" in content  # Разделитель строк таблицы

    def test_parse_removes_scripts_and_styles(self) -> None:
        """Удаление скриптов и стилей."""
        html = """
        <html>
        <head>
            <style>body { color: red; }</style>
        </head>
        <body>
            <h1>Заголовок</h1>
            <p>Текст</p>
            <script>alert('test');</script>
        </body>
        </html>
        """

        parser = HTMLParser()
        sections = parser.parse(html)

        assert len(sections) == 1
        assert "Текст" in sections[0].content
        assert "alert" not in sections[0].content
        assert "color: red" not in sections[0].content

    def test_parse_empty_sections_skipped(self) -> None:
        """Пустые секции пропускаются."""
        html = """
        <html>
        <body>
            <h1>Секция с контентом</h1>
            <p>Контент</p>
            <h1>Пустая секция</h1>
            <h1>Ещё секция</h1>
            <p>Текст</p>
        </body>
        </html>
        """

        parser = HTMLParser()
        sections = parser.parse(html)

        # Должны быть только секции с контентом
        assert len(sections) == 2
        assert sections[0].header == "Секция с контентом"
        assert sections[1].header == "Ещё секция"
