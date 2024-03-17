import sys

from crossword import *


class CrosswordCreator():

    def __init__(self, crossword):
        """
        Create new CSP crossword generate.
        """
        self.crossword = crossword
        self.domains = {
            var: self.crossword.words.copy()
            for var in self.crossword.variables
        }

    def letter_grid(self, assignment):
        """
        Return 2D array representing a given assignment.
        """
        letters = [
            [None for _ in range(self.crossword.width)]
            for _ in range(self.crossword.height)
        ]
        for variable, word in assignment.items():
            direction = variable.direction
            for k in range(len(word)):
                i = variable.i + (k if direction == Variable.DOWN else 0)
                j = variable.j + (k if direction == Variable.ACROSS else 0)
                letters[i][j] = word[k]
        return letters

    def print(self, assignment):
        """
        Print crossword assignment to the terminal.
        """
        letters = self.letter_grid(assignment)
        for i in range(self.crossword.height):
            for j in range(self.crossword.width):
                if self.crossword.structure[i][j]:
                    print(letters[i][j] or " ", end="")
                else:
                    print("█", end="")
            print()

    def save(self, assignment, filename):
        """
        Save crossword assignment to an image file.
        """
        from PIL import Image, ImageDraw, ImageFont
        cell_size = 100
        cell_border = 2
        interior_size = cell_size - 2 * cell_border
        letters = self.letter_grid(assignment)

        # Create a blank canvas
        img = Image.new(
            "RGBA",
            (self.crossword.width * cell_size,
             self.crossword.height * cell_size),
            "black"
        )
        font = ImageFont.truetype("assets/fonts/OpenSans-Regular.ttf", 80)
        draw = ImageDraw.Draw(img)

        for i in range(self.crossword.height):
            for j in range(self.crossword.width):

                rect = [
                    (j * cell_size + cell_border,
                     i * cell_size + cell_border),
                    ((j + 1) * cell_size - cell_border,
                     (i + 1) * cell_size - cell_border)
                ]
                if self.crossword.structure[i][j]:
                    draw.rectangle(rect, fill="white")
                    if letters[i][j]:
                        _, _, w, h = draw.textbbox((0, 0), letters[i][j], font=font)
                        draw.text(
                            (rect[0][0] + ((interior_size - w) / 2),
                             rect[0][1] + ((interior_size - h) / 2) - 10),
                            letters[i][j], fill="black", font=font
                        )

        img.save(filename)

    def solve(self):
        """
        Enforce node and arc consistency, and then solve the CSP.
        """
        self.enforce_node_consistency()
        self.ac3()
        return self.backtrack(dict())

    def enforce_node_consistency(self):
        """
        Update `self.domains` such that each variable is node-consistent.
        (Remove any values that are inconsistent with a variable's unary
         constraints; in this case, the length of the word.)
        """
        for var in self.domains.keys():
            invalid_words = [word for word in self.domains[var] if len(word) != var.length]
            for word in invalid_words:
                self.domains[var].remove(word)
            
        
        

    def revise(self, x, y):
        """
        Make variable `x` arc consistent with variable `y`.
        To do so, remove values from `self.domains[x]` for which there is no
        possible corresponding value for `y` in `self.domains[y]`.

        Return True if a revision was made to the domain of `x`; return
        False if no revision was made.
        """
        revised = False
        overlap = self.crossword.overlaps[x, y]
    
        if overlap:
            i, j = overlap
            for word_x in list(self.domains[x]):
                if not any(i < len(word_x) and j < len(word_y) and word_x[i] == word_y[j] for word_y in self.domains[y]):
                    self.domains[x].remove(word_x)
                    revised = True
                    
        return revised


    def ac3(self, arcs=None):
        """
        Update `self.domains` such that each variable is arc consistent.
        If `arcs` is None, begin with initial list of all arcs in the problem.
        Otherwise, use `arcs` as the initial list of arcs to make consistent.

        Return True if arc consistency is enforced and no domains are empty;
        return False if one or more domains end up empty.
        """
        if arcs is None:
            arcs = [(x, y) for x in self.crossword.variables for y in self.crossword.variables if x != y]

        while arcs:
            x, y = arcs.pop(0)
            if self.revise(x, y):
                if not self.domains[x]:
                    return False
                for z in self.crossword.neighbors(x):
                    if z != y:
                        arcs.append((z, x))
        return True

    def assignment_complete(self, assignment):
        """
        Return True if `assignment` is complete (i.e., assigns a value to each
        crossword variable); return False otherwise.
        """
        return set(assignment.keys()) == set(self.crossword.variables)

    def consistent(self, assignment):
        """
        Return True if `assignment` is consistent (i.e., words fit in crossword
        puzzle without conflicting characters); return False otherwise.
        """
            # 1. Check for distinct values
        if len(set(assignment.values())) != len(assignment.values()):
            return False
        
        # 2. Check for correct lengths
        for var, word in assignment.items():
            if var.length != len(word):
                return False

        # 3. Check for conflicts between neighboring variables
        for var1, word1 in assignment.items():
            for var2, word2 in assignment.items():
                if var1 != var2 and self.crossword.overlaps.get((var1, var2)):  # Using .get() to avoid KeyError
                    overlap = self.crossword.overlaps[(var1, var2)]
                    if word1[overlap[0]] != word2[overlap[1]]:
                        return False

        return True


    def order_domain_values(self, var, assignment):
        """
        Return a list of values in the domain of `var`, in order by
        the number of values they rule out for neighboring variables.
        The first value in the list, for example, should be the one
        that rules out the fewest values among the neighbors of `var`.
        """
            # Function to count the number of ruled-out choices for neighboring unassigned variables
        def count_conflicts(value):
            count = 0
            for neighbor in self.crossword.neighbors(var):
                if neighbor not in assignment:
                    overlap = self.crossword.overlaps[(var, neighbor)]
                    for neighbor_value in self.domains[neighbor]:
                        if value[overlap[0]] != neighbor_value[overlap[1]]:
                            count += 1
            return count

        # Sort the domain values based on least-constraining values heuristic
        domain_values = list(self.domains[var])
        domain_values.sort(key=lambda value: count_conflicts(value))
        
        return domain_values

    def select_unassigned_variable(self, assignment):
        """
        Return an unassigned variable not already part of `assignment`.
        Choose the variable with the minimum number of remaining values
        in its domain. If there is a tie, choose the variable with the highest
        degree. If there is a tie, any of the tied variables are acceptable
        return values.
        """
            # Function to compute the number of remaining values for a variable
        def num_remaining_values(variable):
            return len(self.domains[variable])

        # Sort unassigned variables by number of remaining values and then by degree
        unassigned_vars = [var for var in self.crossword.variables if var not in assignment]
        unassigned_vars.sort(key=lambda var: (num_remaining_values(var), -len(self.crossword.neighbors(var))))
        
        # Return the variable with the minimum remaining values and the maximum degree
        return unassigned_vars[0]

    def backtrack(self, assignment):
        """
        Using Backtracking Search, take as input a partial assignment for the
        crossword and return a complete assignment if possible to do so.

        `assignment` is a mapping from variables (keys) to words (values).

        If no assignment is possible, return None.
        """
                # Check if the assignment is complete
        if self.assignment_complete(assignment):
            return assignment
        
        # Select an unassigned variable using the MRV and degree heuristics
        var = self.select_unassigned_variable(assignment)
        
        # Try assigning values to the selected variable
        for value in self.order_domain_values(var, assignment):  # <-- Pass 'assignment' here
          if self.consistent(assignment):
                assignment[var] = value
                
                # Recursive call
                result = self.backtrack(assignment)
                
                # If a valid assignment is found, return it
                if result:
                    return result
                
                # Otherwise, backtrack and try the next value
                del assignment[var]
        
        # If no value leads to a valid assignment, return None
        return None


def main():

    # Check usage
    if len(sys.argv) not in [3, 4]:
        sys.exit("Usage: python generate.py structure words [output]")

    # Parse command-line arguments
    structure = sys.argv[1]
    words = sys.argv[2]
    output = sys.argv[3] if len(sys.argv) == 4 else None

    # Generate crossword
    crossword = Crossword(structure, words)
    creator = CrosswordCreator(crossword)
    assignment = creator.solve()

    # Print result
    if assignment is None:
        print("No solution.")
    else:
        creator.print(assignment)
        if output:
            creator.save(assignment, output)


if __name__ == "__main__":
    main()
