import keyword
import random
import re
from operator import methodcaller

from deepdiff import DeepDiff
from typing_extensions import Self

FOUR_SPACES = "    "
TWO_SPACES = "  "
STATEMENTS = ["cj9_kappa", "kindly_kappas", "buggy_feature", "jammers"]

STARTSWITH_DEF_REGEX = re.compile(r"^\s*(async\s+def|def)\s(.*):")


class Modifiers:
    """A set of code modifying methods."""

    def __init__(self, file_contents: list[str], difficulty: int = 1) -> None:
        """This class has different functions which introduce different types of bugs.

        All the functions should return Self so they can be chained to get the final
        output. The number of chained functions is determined by the difficulty but
        they are randomly sampled across the entire codebase.

        Args:
            file_contents: The raw data received from the websocket.
            difficulty: The level of difficulty selected. Defaults to 1.
        """
        self.file_contents = file_contents[:-1]  # Removes the last "\n"
        self.difficulty = difficulty

        self.modified_contents = file_contents[:-1]

    @property
    def output(self) -> list[tuple[int, str]] | list:
        """Returns the modified code, if any modifications have been done.

        Returns:
            Only the modified lines of code, including the line number.
        """
        method_names = [
            func for func in dir(Modifiers) if callable(getattr(Modifiers, func)) and not func.startswith("__")
        ]
        methods = map(methodcaller, random.sample(method_names, self.difficulty))

        for method in list(methods):
            method(self)

        diff = DeepDiff(self.file_contents, self.modified_contents)
        line_diffs = []

        try:
            for line_num, values in diff["values_changed"].items():
                (num,) = list(filter(lambda x: x.isdigit(), re.split(r"(\d*)", line_num)))
                new_value = values["new_value"]
                line_diffs.append((int(num), new_value))
        except KeyError:
            # No values were changed
            pass

        return line_diffs

    def remove_indentation(self) -> Self:
        """A code modifier that causes an IndentationError.

        This will reduce indentation from four spaces to two spaces.

        Returns:
            The modifier instance.
        """
        line_numbers = []
        for num, line in enumerate(self.file_contents):
            if line.startswith(FOUR_SPACES):
                line_numbers.append(num)

        line_subset = random.sample(line_numbers, min(self.difficulty, len(line_numbers)))
        for num in line_subset:
            self.modified_contents[num] = self.modified_contents[num].replace(FOUR_SPACES, TWO_SPACES)

        return self

    def remove_end_colon(self) -> Self:
        """A code modifier that causes a SyntaxError.

        This will remove the colon after a function definition, loop, or if statement.

        Returns:
            The modifier instance.
        """
        line_numbers = []
        for num, line in enumerate(self.file_contents):
            if line.endswith(":\n"):
                line_numbers.append(num)

        line_subset = random.sample(line_numbers, min(self.difficulty, len(line_numbers)))
        for num in line_subset:
            self.modified_contents[num] = self.modified_contents[num].replace(":", "")

        return self

    def change_keyword(self) -> Self:
        """A code modifier that causes a SyntaxError.

        This will change any of the python keywords.

        Returns:
            The modifier instance.
        """
        python_keywords = keyword.kwlist

        number_keyword_pairs = []
        for num, line in enumerate(self.file_contents):
            if any(key in line for key in python_keywords):
                number_keyword_pairs.extend([(num, key) for key in python_keywords if key in line])

        line_subset = random.sample(number_keyword_pairs, min(self.difficulty, len(number_keyword_pairs)))
        for num, key in line_subset:
            self.modified_contents[num] = self.modified_contents[num].replace(key, random.choice(STATEMENTS))

        return self

    def comment(self) -> Self:
        """A code modifier that could raise an error.

        This will comment out a line of code.

        Returns:
            The modifier instance.
        """
        line_numbers = []
        for num, line in enumerate(self.file_contents):
            if line != "\n":
                line_numbers.append(num)

        line_subset = random.sample(line_numbers, min(self.difficulty, len(line_numbers)))
        for num in line_subset:
            self.modified_contents[num] = f"# {self.modified_contents[num]}"

        return self

    def change_function_call_name(self) -> Self:
        """A code modifier that causes a NameError.

        Where a function is called, the name of that function will be changed.

        Returns:
            The modifier instance.
        """
        function_names = []
        for num, line in enumerate(self.file_contents):
            match = STARTSWITH_DEF_REGEX.match(line)

            if match:
                func_name = match.groups()[1].split("(")[0]

                # Don't include dunder methods
                if func_name.startswith("__"):
                    continue

                # If the method is a property, don't use it as it's not callable
                if self.file_contents[num - 1] == f"{FOUR_SPACES}@property\n":
                    continue

                function_names.append((num, func_name))

        line_subset = random.sample(function_names, min(self.difficulty, len(function_names)))
        for num, line in enumerate(self.file_contents):
            for def_num, func_name in line_subset:
                if num == def_num:
                    continue

                func_match = re.match(rf".*\.?({func_name}\().*", line)

                if func_match:
                    self.modified_contents[num] = self.modified_contents[num].replace(
                        func_name, random.choice(STATEMENTS)
                    )

        return self

    def insert_empty_statements(self) -> Self:
        """A code modifier that causes an IndentationError.

        This will randomly insert empty if statements.

        Returns:
            The modifier instance.
        """
        total_length = len(self.file_contents)
        random_position = random.randrange(total_length)

        statement = f"if {random.choice(STATEMENTS)}\n"
        self.modified_contents[random_position] = f"{self.modified_contents[random_position]}\n{statement}"

        return self


if __name__ == "__main__":
    test_lines = [
        "def say_hello() -> str:\n",
        '    return "Hello!"\n',
        "say_hello()\n",
        "\n",
    ]

    modifiers = Modifiers(test_lines)
    print(modifiers.output)
