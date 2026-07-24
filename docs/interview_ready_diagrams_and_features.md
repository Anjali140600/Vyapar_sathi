# Interview Ready Answers

## User Flow Diagram Answer

In my project, the user flow starts from the login or signup page. If the user is not authenticated, they first create an account or log in. After successful login, the JWT token is stored on the client side, and the user is redirected to the dashboard.

From the dashboard, the user can move to five main modules:

1. Dashboard
2. Transactions
3. AI Assistant
4. Bill Upload
5. Reports

On the **Dashboard**, the user sees business summary data such as total sales, expenses, profit, GST, recent transactions, and quick action buttons.

In the **Transactions** module, the user can add, view, search, edit, duplicate, and delete transaction records. This is the main ledger management flow.

In the **AI Assistant** module, the user can ask business questions like total sales or expenses, GST questions, upload a bill, upload a voice file, or use live microphone recording. The system then processes the input and gives a response.

In the **Bill Upload** module, the user uploads an invoice or bill image. OCR extracts important details such as amount, date, and category. The user can review the extracted fields and save them as a transaction.

In the **Reports** module, the user views charts and insights such as profit trends, top expense categories, income sources, and overall business performance.

So in short, the user flow is:

`Login/Register -> Dashboard -> Transactions / Assistant / Upload / Reports -> Data saved and insights shown`

### One-line interview version

The user first authenticates, then accesses the dashboard, from where they can manage transactions, scan bills, chat with the assistant, and view reports.

## Data Flow Diagram Answer

The data flow in my project begins from the React frontend. The frontend sends API requests to the FastAPI backend.

The backend has four main API groups:

1. Auth API
2. Transaction API
3. Chat API
4. Multimodal API

For **authentication**, user signup and login data go from frontend to backend, and user credentials are stored in MySQL. After login, the backend generates a JWT token and sends it back to the frontend.

For **transactions**, the frontend sends transaction data such as amount, category, GST, quantity, and date to the backend. The backend validates the data and stores it in the MySQL `transactions` table. When the user opens dashboard or reports, the backend fetches transaction data from MySQL and sends it back to the frontend.

For **assistant queries**, the frontend sends the user message to the chat API. Then the chat orchestrator classifies the query:

- If it is a business data query, it goes to MySQL through the data service.
- If it is a GST knowledge query, it goes to ChromaDB through the RAG service.
- If it is mixed, the system combines both results.

Then the final response is sent back to the frontend and also stored in MySQL chat tables like conversations and messages.

For **bill upload**, the user uploads an image file. The file is stored in the `uploads` folder, metadata is stored in MySQL, and OCR processes the image to extract text and bill details. That extracted data is either shown to the user for review or passed into assistant flow.

For **voice input**, the browser records audio, sends it to the backend, and the backend uses Whisper-based STT to convert speech to text. That text is then used in the assistant workflow. The live recording is temporary and not permanently stored as an audio file in this flow.

So the main data flow is:

`Frontend -> FastAPI Backend -> MySQL for structured data`

`Frontend -> FastAPI Backend -> ChromaDB for GST semantic retrieval`

`Frontend -> FastAPI Backend -> uploads folder for files -> OCR/STT processing`

### One-line interview version

The frontend sends requests to FastAPI, FastAPI stores structured business data in MySQL, stores uploaded files in local storage, and uses ChromaDB to answer GST knowledge queries.

## What Are the Features of My Project

Your project, **Vyapar Sathi**, has these main features:

1. **User Authentication**
   - User signup and login
   - JWT-based secure access
   - Protected pages after login

2. **Dashboard**
   - Shows total sales, total expenses, profit, and GST tracked
   - Displays recent transactions
   - Gives quick actions like add transaction, upload bill, and ask assistant

3. **Transaction Management**
   - Add income and expense entries
   - Edit, delete, search, and filter transactions
   - Duplicate old transactions for faster entry
   - Store amount, GST, quantity, date, category, and notes

4. **AI Finance Assistant**
   - Users can ask business questions like total sales, expenses, profit, rent, GST amount
   - Supports chat sessions and chat history
   - Automatically decides whether to answer from business data or GST knowledge base

5. **GST Knowledge Assistant**
   - Answers GST-related questions using document-based retrieval
   - Uses ChromaDB for semantic search over GST PDFs
   - Useful for tax, GST rules, CGST/SGST/IGST, slabs, and related queries

6. **Bill Upload and OCR**
   - Upload invoice or bill images
   - Extract text and important details like amount and date
   - Review extracted data before saving
   - Save scanned bill as a transaction

7. **Voice Input**
   - Upload voice file for transcription
   - Live microphone recording in browser
   - Speech converted to text using Whisper
   - Transcribed text can be sent to the assistant

8. **Reports and Insights**
   - Profit trend charts
   - Expense category analysis
   - Income source breakdown
   - Business performance summary

9. **Multimodal Support**
   - Accepts text, image, and voice input
   - OCR for images
   - STT for audio
   - Integrates these inputs into assistant workflow

10. **Small Business Friendly Design**
   - Built for Indian small businesses
   - Tracks day-to-day ledger activity in a simple way
   - Includes GST-focused functionality

## Best interview answer

“My project is a smart business diary for small businesses. It includes login, transaction management, dashboard analytics, bill scanning with OCR, voice input, AI-based business question answering, GST knowledge retrieval using ChromaDB, and reports for sales, expenses, profit, and category insights.”
