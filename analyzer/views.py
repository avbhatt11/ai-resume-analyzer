from groq import Groq
import PyPDF2
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Avg
from .models import Resume

client = Groq(api_key="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")


def extract_text_from_pdf(pdf_file):
    try:
        reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted
        return text
    except Exception as e:
        return f"Error reading PDF: {str(e)}"


def analyze_with_ai(resume_text):
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "user",
                    "content": f"""
                    Analyze this resume and provide:
                    1. Top 5 Skills found
                    2. Suggested Job Roles (3 roles)
                    3. Resume Strengths (2-3 points)
                    4. Areas of Improvement (2-3 points)
                    5. Overall Score out of 100

                    Resume:
                    {resume_text}

                    Give response in clean format with headings.
                    """
                }
            ],
            max_tokens=1000
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"AI Analysis Error: {str(e)}"


def extract_score(feedback_text):
    import re
    patterns = [
        r'(\d{1,3})\s*/\s*100',
        r'(\d{1,3})\s+out\s+of\s+100',
        r'score[:\s]+(\d{1,3})',
        r'overall[:\s]+(\d{1,3})',
    ]
    for pattern in patterns:
        match = re.search(pattern, feedback_text, re.IGNORECASE)
        if match:
            score = int(match.group(1))
            if 0 <= score <= 100:
                return score
    return 75


def home(request):
    resumes = Resume.objects.all()
    total = resumes.count()
    avg_score = resumes.aggregate(avg=Avg('score'))['avg'] or 0
    top_candidates = resumes.order_by('-score')[:4]

    context = {
        'total_resumes': total,
        'avg_score': round(avg_score),
        'top_candidates': top_candidates,
    }
    return render(request, 'analyzer/home.html', context)


def upload_resume(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        resume_file = request.FILES.get('resume_file')

        if not resume_file:
            return render(request, 'analyzer/upload.html', {
                'error': 'Please upload a PDF file.'
            })

        resume_text = extract_text_from_pdf(resume_file)

        if not resume_text or resume_text.startswith("Error"):
            return render(request, 'analyzer/upload.html', {
                'error': 'Could not read PDF. Please upload a valid PDF file.'
            })

        ai_feedback = analyze_with_ai(resume_text)
        score = extract_score(ai_feedback)

        resume = Resume.objects.create(
            name=name,
            email=email,
            resume_file=resume_file,
            ai_feedback=ai_feedback,
            score=score
        )

        return redirect('result', resume_id=resume.id)

    return render(request, 'analyzer/upload.html')


def result(request, resume_id):
    resume = get_object_or_404(Resume, id=resume_id)
    return render(request, 'analyzer/result.html', {
        'name': resume.name,
        'feedback': resume.ai_feedback,
        'score': resume.score,
        'email': resume.email,
        'resume_id': resume.id,
    })