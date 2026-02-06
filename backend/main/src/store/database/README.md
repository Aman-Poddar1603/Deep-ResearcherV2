in this "database/" folder, we have the list of the sqlite databases uses in the project. Each database is designed to store specific types of data. and the databases are generated automatically when the project is run for the first time. 

Required databases:
- **Basic Information Database**: This database is used to store basic information about the user, such as their name, srttings, preferences, email, and other relevant details that can help in personalizing the user experience within the application.
    - db_name: `basic_info.db.sqlite3`
- **History Database**: This database is used to store the history of user interactions, including queries made, responses received, and any other relevant information that can help in tracking the user's activity within the application.
    - db_name: `history.db.sqlite3`
- **Bucket Database**: This database is used to manage the buckets created by users. It stores information about each bucket, such as its name, creation date, and any metadata associated with it.
    - db_name: `bucket.db.sqlite3`
- **Scrape Database**: This database is used to store the data scraped from various sources. It can include information such as the source URL, the content scraped, and any relevant metadata that can help in organizing and retrieving the scraped data efficiently.
    - db_name: `scrape.db.sqlite3`
- **Research Database**: This database is used to store the research data generated from user interactions and queries. It can include information such as the research topic, the data collected, and any insights or conclusions drawn from the research process.
    - db_name: `research.db.sqlite3`
- **Chat Database**: This database is used to manage the chat of the user. It stores information about each chat, such as its name, creation date, and any metadata associated with it.
    - db_name: `chat.db.sqlite3`
- **Exports Database**: This database is used to manage the exports of the user. It stores information about each export, such as its name, creation date, and any metadata associated with it.
    - db_name: `exports.db.sqlite3`
