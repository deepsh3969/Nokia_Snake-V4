import os


class HighScore:

    def __init__(
        self,
        filename="highscore.dat"
    ):

        self.filename = os.path.join(

            os.path.dirname(
                os.path.abspath(__file__)
            ),

            filename
        )

        self.value = self.load()

    def load(self):

        try:

            if not os.path.exists(
                self.filename
            ):

                return 0

            with open(
                self.filename,
                "r"
            ) as file:

                return int(
                    file.read().strip()
                )

        except Exception:

            return 0

    def get(self):

        return self.value

    def save(
        self,
        score
    ):

        if score <= self.value:

            return

        self.value = score

        try:

            with open(
                self.filename,
                "w"
            ) as file:

                file.write(
                    str(self.value)
                )

        except Exception as error:

            print(
                "High score error:",
                error
            )