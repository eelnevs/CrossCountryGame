from CountryNeighbors import CountryNeighbors

game = CountryNeighbors()

play = input("Guess Shortest Path? (y/N) ")
while play.lower() == "yes" or play.lower() == "y":
    start_country = input("Enter start country: ")
    start = game.get_country_code_from_input(start_country)
    if start == -1:
        print("Country not found, please try again.")
        continue
    while True:
        end_country = input("Enter end country: ")
        end = game.get_country_code_from_input(end_country)
        if end == -1:
            print("Country not found, please try again.")
            continue
        else:
            break
    country_path = game.find_shortest_path(start, end)
    print("Shortest path:", end=" ")
    if (country_path):
        print(" -> ".join(country_path))
        print(f"Crossing {str(len(country_path) - 2)} countries")
    else:
        print("Not found")
    print()
    if input("Check list? (y/N) ").lower() in ["y", 'yes']:
        game.check_lists(start)
    if input("Press Enter to play again. Enter any other key to quit.\n"):
        break

