# FAIR: Fast AI-Assisted Investigation and Review

**FAIR** is an AI-assisted investigation and review system developed for the New Jersey Attorney Generals Office Division on Civil Rights (DCR) to streamline case handling, improve documentation consistency, and accelerate investigative workflows.

<div>
    <a href="https://www.loom.com/share/cc17300943024212ab192660a3616a1f">
    </a>
    <a href="https://www.loom.com/share/cc17300943024212ab192660a3616a1f">
      <img style="max-width:300px;" src="https://cdn.loom.com/sessions/thumbnails/cc17300943024212ab192660a3616a1f-e9de020951c4e758-full-play.gif">
    </a>
  </div>

## What It Does
NJ FAIR provides an AI-assisted investigation and review system with three key components:

#### **Transcript Processing**
- Converts video recordings into structured, searchable transcripts  
- Significantly improves accuracy by 36% compared to current Microsoft Teams transcription  
- Creates consistent documentation that follows standardized formatting  

#### **Interview Summarization**
- Generates concise, context-aware summaries based on transcripts  
- Structures summaries according to DCR's preferred format for investigative documentation  
- Highlights key elements such as allegations, respondent statements, and supporting evidence  
- Easy ‘revision’ button to alter summary based on additional context or personal preferences  

#### **Interactive Chat Interface**
- Allows users to ask natural language questions about the interview content  
- Retrieves targeted insights without requiring full transcript review  
- Enables efficient information retrieval without technical search expertise

## Architecture
![Architecture Flow](https://github.com/arinjay-singh/interview-summary-tool/blob/0e30114ee274d0705e4bb1d8e8d8a7cf8b94a325/Technical%20Arc%20Diagram.png)

## Tech Stack
| Layer              | Tools & Frameworks                                                                 |
|--------------------|------------------------------------------------------------------------------------|
| **Frontend**        | Next.js, Tailwind CSS, Azure Static Web Apps                                      |
| **Backend**         | Flask (Python), Azure Container Apps, Docker, Azure Container Registry (ACR)      |
| **Database**        | PostgreSQL, Azure Database for PostgreSQL                                         |
| **AI/ML**           | GPT4o Transcribe (OpenAI), GPT-4o (OpenAI)                                                 |
| **Security & Networking** | Secruity through the cloud            |
| **Infra/DevOps**    | Docker, Azure Container Registry, Azure Infrastructure (scalable, highly available) |
| **Data Privacy**    | Uploaded documents are not stored; they are deleted immediately after processing   |

## Setup
#### Clone the Repo
git clone https://github.com/arinjay-singh/interview-summary-tool/tree/main  \
cd project-name

#### Install Dependencies
pip install -r requirements.txt

#### Run Locally
???

## Contributions
If you are contributing please follow these steps:

1. Fork the repository.
2. Create a new branch (`git checkout -b feature/YourFeature`).
3. Make your changes and commit them (`git commit -m 'Add some feature'`).
4. Push to the branch (`git push origin feature/YourFeature`).
5. Open a pull request.

## License
MIT License – see `LICENSE` for details.

## Authors & Acknowledgements
Built by Arinjay Singh & Dhruv Reddy Tekulapalli  \
In partnership with the New Jersey Attorney Generals Office Divison on Civil Rights
