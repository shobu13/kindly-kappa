import pytest

from server.modifiers import FOUR_SPACES, STATEMENTS, Modifiers

test_input = [
    "def say_hello() -> str:\n",
    '    return "Hello!"\n',
    "say_hello()\n",
    "\n",
]


@pytest.fixture
def create_instance():
    yield Modifiers(test_input)


@pytest.fixture
def create_instance_with_dunder():
    dunder_input = ["class Test:\n", "    def __init__(self) -> None:\n", "        ...\n", "\n"]
    yield Modifiers(dunder_input + test_input)


@pytest.fixture
def create_instance_with_property():
    property_input = ["class Test:\n", "    @property\n", "    def output(self) -> None:\n", "\n"]
    yield Modifiers(property_input + test_input)


class TestModifiers:
    def test_removing_indentation(self, create_instance: Modifiers):
        value = create_instance.remove_indentation()

        assert isinstance(value, Modifiers)
        assert value.file_contents[1].startswith(FOUR_SPACES)
        assert value.modified_contents == [
            "def say_hello() -> str:\n",
            '  return "Hello!"\n',
            "say_hello()\n",
        ]

    def test_removing_end_colon(self, create_instance: Modifiers):
        value = create_instance.remove_end_colon()

        assert isinstance(value, Modifiers)
        assert ":" in value.file_contents[0]
        assert value.modified_contents == [
            "def say_hello() -> str\n",
            '    return "Hello!"\n',
            "say_hello()\n",
        ]

    def test_keyword_changing(self, create_instance: Modifiers):
        value = create_instance.change_keyword()

        assert isinstance(value, Modifiers)
        assert any(stmt in modified for stmt in STATEMENTS for modified in value.modified_contents)

    def test_commenting_code(self, create_instance: Modifiers):
        value = create_instance.comment()

        assert isinstance(value, Modifiers)
        assert any(line.startswith("#") for line in value.modified_contents)

    def test_changing_function_call_names(self, create_instance: Modifiers):
        value = create_instance.change_function_call_name()

        assert isinstance(value, Modifiers)
        assert any(stmt in modified for stmt in STATEMENTS for modified in value.modified_contents)

    def test_changing_function_call_names_with_dunder_functions(self, create_instance_with_dunder: Modifiers):
        value = create_instance_with_dunder.change_function_call_name()

        assert isinstance(value, Modifiers)
        assert any(stmt in modified for stmt in STATEMENTS for modified in value.modified_contents)

    def test_changing_function_call_names_with_property_decorator(self, create_instance_with_property: Modifiers):
        value = create_instance_with_property.change_function_call_name()

        assert isinstance(value, Modifiers)
        assert any(stmt in modified for stmt in STATEMENTS for modified in value.modified_contents)

    def test_inserting_an_empty_if_statement(self, create_instance: Modifiers):
        value = create_instance.insert_empty_statements()

        assert isinstance(value, Modifiers)
        assert any(stmt in modified for stmt in STATEMENTS for modified in value.modified_contents)

    @pytest.mark.parametrize("difficulty", (1, 2, 3))
    def test_modified_output(self, create_instance: Modifiers, difficulty: int):
        create_instance.difficulty = difficulty
        value = create_instance.output

        assert create_instance.difficulty == difficulty
        assert isinstance(value, list)
        assert difficulty <= create_instance.modified_count
