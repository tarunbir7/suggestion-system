from flask import Flask, render_template, request
import requests
import random

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

def get_all_problems():
    url = "https://leetcode.com/api/problems/all/"
    response = requests.get(url)
    
    if response.status_code == 200:
        try:
            data = response.json()
            return data.get("stat_status_pairs", [])
        except (KeyError, ValueError):
            print("❌ Error: Could not parse LeetCode problem data.")
            return []
    else:
        print(f"❌ Error: LeetCode API request failed with status code {response.status_code}")
        return []

def get_leetcode_data(username):
    url = "https://leetcode.com/graphql"
    query = """
        {
            matchedUser(username: "%s") {
                submissions(first: 100) {
                    edges {
                        node {
                            status
                            titleSlug
                        }
                    }
                }
            }
        }
    """ % username
    
    response = requests.post(url, json={"query": query})
    
    try:
        data = response.json()
        if "data" in data and data["data"].get("matchedUser") and data["data"]["matchedUser"].get("submissions") and data["data"]["matchedUser"]["submissions"].get("edges"):
            solved_problems = {edge["node"]["titleSlug"] for edge in data["data"]["matchedUser"]["submissions"]["edges"] if edge["node"]["status"] == "AC"}
            return solved_problems
        else:
            print("⚠️ No data found for the given username.")
            return set()
    except Exception as e:
        print(f"❌ Error when parsing LeetCode data: {str(e)}")
        return set()

def get_problem_details(title_slug):
    """Fetch detailed information about a specific problem including topics/tags"""
    url = "https://leetcode.com/graphql"
    query = """
        {
            question(titleSlug: "%s") {
                title
                titleSlug
                difficulty
                topicTags {
                    name
                    slug
                }
            }
        }
    """ % title_slug
    
    try:
        response = requests.post(url, json={"query": query})
        if response.status_code == 200:
            data = response.json()
            if "data" in data and "question" in data["data"]:
                return data["data"]["question"]
        return None
    except Exception as e:
        print(f"❌ Error fetching problem details: {str(e)}")
        return None

def suggest_problem(username, difficulty=None, topic=None):
    solved_problems = get_leetcode_data(username)
    all_problems = get_all_problems()
    
    if not all_problems:
        return "Error fetching problem data from LeetCode."
    
    # Convert difficulty to expected format (1=Easy, 2=Medium, 3=Hard)
    difficulty_map = {"easy": 1, "medium": 2, "hard": 3}
    if difficulty and difficulty.lower() in difficulty_map:
        difficulty_value = difficulty_map[difficulty.lower()]
    else:
        difficulty_value = None
    
    # Filter problems by difficulty first
    if difficulty_value:
        difficulty_filtered = [p for p in all_problems if p.get("difficulty", {}).get("level") == difficulty_value]
    else:
        difficulty_filtered = all_problems
    
    # Further filter to only unsolved problems
    unsolved_problems = [p for p in difficulty_filtered 
                          if p["stat"]["question__title_slug"] not in solved_problems]
    
    if not unsolved_problems:
        return "No unsolved problems found with the selected criteria."
    
    # If topic is specified, we need to check each problem's details
    if topic:
        topic = topic.lower()
        topic_filtered = []
        
        # Try more problems to increase chances of finding a match
        check_limit = min(50, len(unsolved_problems))
        random_sample = random.sample(unsolved_problems, check_limit)
        
        print(f"Checking {check_limit} problems for topic: {topic}")
        
        for problem in random_sample:
            slug = problem["stat"]["question__title_slug"]
            details = get_problem_details(slug)
            
            if details and "topicTags" in details:
                # Print for debugging
                problem_topics = [tag["name"].lower() for tag in details["topicTags"]]
                print(f"Problem: {slug}, Topics: {problem_topics}")
                
                # Check if any topic contains our search term (partial match)
                if any(topic in tag.lower() for tag in problem_topics):
                    topic_filtered.append(problem)
                    print(f"Found matching problem: {slug}")
        
        if topic_filtered:
            selected_problem = random.choice(topic_filtered)
        else:
            # If no exact matches found, return a random unsolved problem
            print("No problems found with the specified topic. Selecting a random problem.")
            selected_problem = random.choice(unsolved_problems)
            return f"No problems found matching '{topic}'. Here's a random problem instead: {selected_problem['stat']['question__title']}"
    else:
        # No topic filter, just pick from unsolved problems
        selected_problem = random.choice(unsolved_problems)
    
    return selected_problem["stat"]["question__title"]

def get_available_topics():
    """Get a list of common LeetCode topics for the dropdown menu"""
    return [
        "Array", "String", "Hash Table", "Dynamic Programming", 
        "Math", "Sorting", "Greedy", "Depth-First Search", 
        "Binary Search", "Database", "Breadth-First Search", 
        "Tree", "Matrix", "Binary Tree", "Two Pointers", 
        "Bit Manipulation", "Stack", "Heap", "Graph", "Linked List"
    ]

@app.route('/suggest', methods=['POST'])
def suggest():
    username = request.form.get('username', '')
    difficulty = request.form.get('difficulty', None)
    topic = request.form.get('topic', None)
    
    if not username:
        return render_template('index.html', message="Please provide a username", topics=get_available_topics())
    
    problem = suggest_problem(username, difficulty, topic)
    message = f"Next suggested problem for {username}: {problem}"
    
    return render_template('index.html', message=message, topics=get_available_topics())

if __name__ == '__main__':
    app.run(debug=True)