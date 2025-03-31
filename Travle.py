from collections import deque
import json
import re
import numpy as np
import pandas as pd
import os.path as op

class Travle:
    filename_code_to_name = "country_code_to_name"
    filename_name_to_code = "country_name_to_code"
    filename_country_neighbors_dict = "country_code_neighbors_dict"

    def __init__(self):
        # global variables
        self.country_name_to_code: dict[str, int] = {}
        self.country_code_to_name: dict[int, str] = {}
        self.country_code_neighbors_dict: dict[int, list[int]] = {}
        # self.list_size = 0
        self.load_data_from_file()
        print("Data loaded")
        self.list_size = len(self.country_name_to_code)
        self.normalized_name_to_code: dict[str, int] = { k.lower():v for k,v in self.country_name_to_code.items()}
        
    def load_data_from_web(self):
        url = "https://en.wikipedia.org/wiki/List_of_countries_and_territories_by_number_of_land_borders"
        tables = pd.read_html(url)
        # get table
        df = tables[0]
        # select only the relevant columns
        df = df.iloc[:, [0, 4, 5]]
        # replace NaN value with blank
        df = df.fillna('')
        # label columns
        df.columns = ["Country", "Number of Neighbors", "Neighbors"]

        ### clean country name
        # clean country name by replacing any [] with letters or numbers
        df["Country"][df["Country"].str.contains('\[[a-z0-9]+\]')] = df["Country"].str.replace('\[[a-z0-9]+\]', "", regex=True)
        df["Country"] = df["Country"].apply(self.clean_country_name)
        # insert additional territories/unrecognized countries
        somaliland = pd.DataFrame({'Country': 'Somaliland', "Number of Neighbors": "1", "Neighbors": ["Djibouti: 61 km (38 mi)"]})
        df = pd.concat([df, somaliland], ignore_index=True)
        french_guiana = pd.DataFrame({'Country': 'French Guiana', "Number of Neighbors": "2", "Neighbors": ["Brazil: 673 km (418 mi)", "Suriname: 510 km (320 mi)"]})
        df = pd.concat([df, french_guiana], ignore_index=True)
        greenland = pd.DataFrame({'Country': 'Greenland', "Number of Neighbors": "1", "Neighbors": ["Canada: 1.2 km (0.75 mi)"]})
        df = pd.concat([df, greenland], ignore_index=True)
        akrotiri_and_dhekelia = pd.DataFrame({'Country': 'Akrotiri and Dhekelia', "Number of Neighbors": "1", "Neighbors": ["Cyprus: 152 km (94 mi)"]})
        df = pd.concat([df, akrotiri_and_dhekelia], ignore_index=True)
        sint_maarten = pd.DataFrame({'Country': 'Sint Maarten', "Number of Neighbors": "1", "Neighbors": ["Saint Martin: 10.2 km (6.3 mi)"]})
        df = pd.concat([df, sint_maarten], ignore_index=True)
        saint_martin = pd.DataFrame({'Country': 'Saint Martin', "Number of Neighbors": "1", "Neighbors": ["Sint Maarten: 10.2 km (6.3 mi)"]})
        df = pd.concat([df, saint_martin], ignore_index=True)
        gibraltar = pd.DataFrame({'Country': 'Gibraltar', "Number of Neighbors": "1", "Neighbors": ["Spain: 1.2 km (0.75 mi)"]})
        df = pd.concat([df, gibraltar], ignore_index=True)

        ### create cleaned_neighbors column
        # clean country neighbors column by replacing any [] or () with letters or numbers
        df["cleaned_neighbors"] = df["Neighbors"]
        df["cleaned_neighbors"][df["Neighbors"].str.contains('\[[a-z0-9]+\]')] = df["Neighbors"].str.replace('\[[a-z0-9]+\]', "", regex=True)
        df["cleaned_neighbors"][df["cleaned_neighbors"].str.contains('\(\d+\)')] = df["cleaned_neighbors"].str.replace('\(\d+\)', "", regex=True)
        # find country names using regex
        df["cleaned_neighbors"] = df["cleaned_neighbors"].apply(self.extract_contry_names)

        ### clean lists
        # Israel is complicated
        df.iat[df.index[df["Country"] == "Israel"][0], 3] = ["Egypt", "Palestine", "Jordan", "Lebanon", "Syria"]
        df.iat[df.index[df["Country"] == "Sweden"][0], 3] = ["Finland", "Norway"]
        # combine same country entries
        df = df.groupby('Country', as_index=False).agg({
            'cleaned_neighbors': lambda x: list(set(sum(x, []))),
            'Number of Neighbors': 'max'
        })
        # print([[ y if y.find("(") != -1 else "" for y in x] for x in df["cleaned_neighbors"].values.tolist()])

        # check number of neighbors
        df["Number of Neighbors"] = pd.to_numeric(df["Number of Neighbors"], errors='coerce').fillna(0).astype(np.int64)
        df["num"] = df["cleaned_neighbors"].apply(len)
        print("Chekcing number of neighbors...")
        print(df.loc[df["Number of Neighbors"] != df["num"]])
        print("done", end="\n\n")

        # make dictionary from country and its neighbors
        country_neighbors_dict: dict[str, list[str]] = dict(zip(df["Country"], df["cleaned_neighbors"]))

        # check country territories
        '''
        Exceptions: 
        Dominica, Dominican Republic
        Guinea, Guinea-Bissau
        Guinea, Papua New Guinea
        Guinea, Equatorial Guinea
        Republic of the Congo, Democratic Republic of the Congo
        '''
        c_keys = sorted(country_neighbors_dict.keys(), key=lambda x: len(x))
        total = len(c_keys)
        print("Checking for potential repeated country...")
        for i, k in enumerate(country_neighbors_dict):
            for j in range(i+1, total):
                c = c_keys[j]
                if c != k and k not in ["Dominica", "Guinea", "Republic of the Congo"] and k in c:
                    print(k, end=', ')
                    print(c)
        print("done", end="\n\n")

        # Country name <-> code dictionaries
        self.country_name_to_code: dict[str, int] = df.reset_index().set_index('Country')["index"].to_dict()
        self.country_code_to_name: dict[int, str] = df["Country"].to_dict()
        # convert country names into country codes for data
        self.country_code = pd.DataFrame(df["Country"].apply(lambda x: self.country_name_to_code.get(x, x)), columns=['Country'])
        self.country_code["Neighbors"] = df["cleaned_neighbors"].apply(lambda x: list(set([self.country_name_to_code.get(c, self.clean_neighbor_list(c)) for c in x])))
        # couple coutries together
        self.couple_countries(["People's Republic of China", "Hong Kong", "Macau"])
        # artificial border crossings
        self.couple_countries(["Malaysia", "Singapore"])
        self.couple_countries(["United Kingdom", "France"])
        self.couple_countries(["Denmark", "Sweden"])
        # decouple Spain and Morocco
        self.decouple_countries(["Spain", "Morocco"])
        # Remove Kaliningrad Oblast connections
        self.decouple_countries(["Russia", "Poland", "Lithuania"])
        # decouple India and Sri Lanka
        self.decouple_countries(["India", "Sri Lanka"])
        # neighbors list dictionary in country codes
        self.country_code_neighbors_dict: dict[int, list[int]] = dict(zip(self.country_code["Country"], self.country_code["Neighbors"]))
        # check if all countries in neighbors list can be found
        print("\nMapping country...")
        print(self.country_code.loc[self.country_code["Neighbors"].apply(lambda x: not all(isinstance(c, int) for c in x))])
        print("done", end="\n\n")
        with open(self.filename_name_to_code, "w") as file:
            file.write(json.dumps(self.country_name_to_code))
        with open(self.filename_code_to_name, "w") as file:
            file.write(json.dumps(self.country_code_to_name))
        with open(self.filename_country_neighbors_dict, "w") as file:
            file.write(json.dumps(self.country_code_neighbors_dict))
        return

    def load_data_from_file(self):
        if op.exists("country_code_to_name") and op.exists("country_name_to_code") and op.exists("country_code_neighbors_dict"):
            print("From file")
            with open(self.filename_code_to_name, "r", encoding='utf-8') as file:
                self.country_code_to_name = {int(k):v for k,v in json.load(file).items()}
            with open(self.filename_name_to_code, "r", encoding='utf-8') as file:
                self.country_name_to_code = json.load(file)
            with open(self.filename_country_neighbors_dict, "r", encoding='utf-8') as file:
                self.country_code_neighbors_dict = {int(k):v for k,v in json.load(file).items()}
        else:
            print("From web")
            self.load_data_from_web()
        return
    
    # extract neighboring country names from list
    def extract_contry_names(slef, html: str):
        '''
        Extract country names in the neighbors list

        The neighbors list generally has the pattern of -- Egypt: 266 km (165 mi)

        Parameters
        ----------
        html : html string scraped from web using pandas for the table column "Neighbors"

        Returns
        ----------
        a list of country names
        '''
        # find country name. Pattern: Egypt: 266 km (165 mi)
        find = re.findall(r"([^\d]+)\d[\d\w\s.,(]+?\)", html)
        if find:
            return [c.replace(u' \xa0', '').replace(u'\xa0', '').replace(':', '').replace('State of ', '').replace(', including Dahagram-Angarpota','').strip() for c in find]
        else:
            return []

    # clean up country name
    def clean_country_name(self, country: str):
        '''
        Clean up the country names in the country list

        Parameters
        ----------
        country : country name

        Returns
        ----------
        cleaned up country name
        '''
        # special case for Macau
        if country == "Macau (People's Republic of China)":
            country = "Macau"
        find = re.findall(r"([^\d]+?)\u2192includes:", country)
        if find:
            country = find[0].strip()
        # simplify some country names
        return country.replace("(constituent country)", '').replace(", Metropolitan", '').strip()

    # search country
    def clean_neighbor_list(self, country: str):
        '''
        Clean up the neighbors list

        Espcially if it's a territory of a country, which has the form [territory (country)]

        Parameters
        ----------
        country : a neighbor country's name

        Returns
        ----------
        cleaned up country/territory name
        '''
        find = re.findall(r"([^\d()]+)\(([^\d]+)\)", country)
        if find:
            t = find[0][0].strip()
            c = find[0][1].strip()
            print(country+" -> "+t+" + "+c)
            return self.country_name_to_code.get(t, self.country_name_to_code.get(c, c))
        return country

    def couple_countries(self, countries: list[str]):
        '''
        Link two or more countries/territories together

        Usually because there is a artificial crossings that Wikipedia didn't count as connected borders.

        Parameters
        ----------
        countries: a list of country names to be linked

        Modifies the country_code DataFrame in place.
        
        No returns
        ----------
        '''
        for c in countries:
            neighbors: list[int] = self.country_code.at[self.country_code.index[self.country_code["Country"] == self.country_name_to_code.get(c)][0], "Neighbors"]
            for c_other in countries:
                if c_other == c:
                    continue
                c_other_code = self.get_country_code(c_other)
                if c_other_code != -1 and c_other_code not in neighbors:
                    neighbors.append(c_other_code)
        return

    def decouple_countries(self, countries: list[str]):
        '''
        Removes two or more countries/territories from each other's neighbors list

        Usually because a territory of a country borders the other countries, but the border is too small and/or 
        the territory is too far away from the main land to be counted as neighbors.

        Parameters
        ----------
        countries: a list of country names to be linked

        Modifies the country_code DataFrame in place.
        
        No returns
        ----------
        '''
        for c in countries:
            neighbors: list[int] = self.country_code.at[self.country_code.index[self.country_code["Country"] == self.country_name_to_code.get(c)][0], "Neighbors"]
            for c_other in countries:
                if c_other != c:
                    try:
                        neighbors.remove(self.country_name_to_code.get(c_other))
                    except ValueError:
                        print(c_other+" not in "+c+"'s list")
        return
    
    def find_shortest_path(self, start_country: int, end_country: int, convert: bool = True):
        '''
        Find shortest path from start_country to end_country
        
        Parameters
        ----------
        start_country : index of the country to start

        end_country : index of the country to end

        convert : convert index code to country name

        Returns
        ----------
        a list of the countries from start to end

        if convert == True -> list[str]

        else -> list[int]
        '''
        dist = [self.list_size + 1]*self.list_size
        prev = [None]*self.list_size
        q = deque()
        q.append(start_country)
        dist[start_country] = 0
        while(len(q) != 0):
            node = q.popleft()
            if (node == end_country):
                break
            for neighbor in self.country_code_neighbors_dict.get(node, []):
                alt = dist[node] + 1
                if alt < dist[neighbor]:
                    dist[neighbor] = alt
                    prev[neighbor] = node
                    q.append(neighbor)
        # find path from start to end country
        path = deque()
        curr = end_country
        if prev[curr] or curr == start_country:
            while curr is not None:
                path.appendleft(curr)
                curr = prev[curr]
        return [self.get_country_name(c) for c in path] if convert else list(path)

    def find_reachable_contries(self, start_country: int):
        '''
        Find all reachable countries from the start_country

        Parameters
        ----------
        start_country : index of the country to start
        
        Returns
        ----------
        a list of distances from start_country with index = index of each country
        '''
        dist = [self.list_size + 1]*self.list_size
        q = deque()
        q.append(start_country)
        dist[start_country] = 0
        print(self.get_country_name(start_country))
        while (len(q) != 0):
            node = q.popleft()
            # print(f'{" "*dist[node]}-> {self.get_country_name(node)}')
            for neighbor in self.country_code_neighbors_dict.get(node, []):
                alt = dist[node] + 1
                if alt < dist[neighbor]:
                    dist[neighbor] = alt
                    q.append(neighbor)
                    print(f"{' '*alt}-> {self.get_country_name(neighbor)}")
        return dist
    
    def dfs(self, start_country: int, visited: list[bool], result: list[int], layer: int):
        visited[start_country] = True
        result.append(start_country)
        print(self.get_country_name(start_country))
        for neighbor in self.country_code_neighbors_dict.get(start_country, []):
            if not visited[neighbor]:
                tabs = "-"*layer
                print(f"{tabs}-> {self.get_country_name(neighbor)}")
                self.dfs(neighbor, visited, result, layer+1)

    def get_country_name(self, code: int):
        return self.country_code_to_name.get(code, "Not Found")
    
    def get_country_code(self, name: str):
        return self.country_name_to_code.get(name, -1)
    
    def get_country_code_from_input(self, name: str):
        return self.normalized_name_to_code.get(name.lower(), -1)
    
    def check_lists(self, start: int):
        '''
        Check the list from Wikipedia vs the reachable list scraped from Travle website

        Parameters
        ----------
        start : index of the start country

        No Return
        ----------
        prints the result on console
        '''
        # check lists
        all_dist = self.find_reachable_contries(start)
        # with open('countries.json', 'r') as file:
        #     country_data = json.load(file)
        with open('reachable_countries.json', 'r', encoding='utf-8') as file:
            reachable_map = json.load(file)
        wiki =[self.get_country_name(i) for i, d in enumerate(all_dist) if d != (self.list_size + 1) and i != start]
        start_country = self.get_country_name(start)
        travle = reachable_map[start_country]
        print(f"find disrepancy for {start_country}...", end="\n\n")
        print("Not in list from Wiki:")
        not_in_wiki = [g for g in travle if g not in wiki]
        if len(not_in_wiki):
            print(end=" "*2)
            print(*not_in_wiki, sep="\n  ")
        else:
            print("  None")
        print()
        print("Not in list from Travle:")
        not_in_travle = [g for g in wiki if g not in travle]
        if len(not_in_travle):
            print(end=" "*2)
            print(*not_in_travle, sep="\n  ")
        else:
            print("  None")
        print()
        if input(f"Show all reachable conuntries from {start_country}? (y/N)").lower() in ["y", "yes"]:
            # all_reachable = [f"{self.get_country_name(i)}: crossing {str(d-1)} countries" for i, d in enumerate(all_dist) if d != (self.list_size + 1) and i != start]
            all_reachable = [[self.get_country_name(i), d] for i, d in enumerate(all_dist) if d != (self.list_size + 1) and i != start]
            all_reachable_sorted = sorted(all_reachable, key=lambda x: x[1])
            print(f"{str(len(all_reachable))} countries reacheable from {start_country}\n")
            print('\n'.join([f'{x[0]}: crossing {str(x[1]-1)} countries' for x in all_reachable_sorted]))
            self.dfs(start, [False]*self.list_size, [], 0)
        print()

