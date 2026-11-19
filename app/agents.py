"""Actual, sequential multi-agent orchestration with independently scoped LLM calls.
No API key / explicit consent => no LLM invocation and no fake AI response.
"""
import json,os,re
from datetime import datetime,timezone
from .models import AgentRun,AgentStep
from .services import compute_summary, LABELS

SYSTEM_RULES="""You are generating an educational, descriptive summary of a person's logged glucose measurements.
This is not clinical care. Never diagnose, predict, suggest medication/supplement doses, tell the patient to stop medication, or assert causal effects. Do not compare readings to medical thresholds or infer medical targets unless independently clinician-provided. Do not imply absent data is normal. Use only supplied numeric evidence. Be concise. No numerical inventions.
Return a JSON object. """

def record(db,run,name,number,status,output):
    db.add(AgentStep(run_id=run.id,agent=name,sequence=number,status=status,output=json.dumps(output,ensure_ascii=False)[:12000]));db.commit()

def llm_json(client,model,system,payload):
    completion=client.chat.completions.create(model=model,temperature=0,response_format={'type':'json_object'},messages=[{'role':'system','content':SYSTEM_RULES+'\n'+system},{'role':'user','content':json.dumps(payload)}])
    return json.loads(completion.choices[0].message.content)

def unsafe(text):
    patterns=[r'\b(increase|decrease|stop|skip|double|adjust|change)\b.{0,35}\b(insulin|medication|dose|tablets?|metformin)\b',r'\bdiagnos(?:e|is|ed)\b',r'\byou (?:definitely|certainly) have\b']
    return any(re.search(p,text,re.I) for p in patterns)

def run_insight_agents(db,user,readings,tasks,client=None):
    if not user.ai_consent:raise ValueError('AI processing requires explicit opt-in')
    model=os.getenv('OPENAI_MODEL','gpt-4o-mini')
    if client is None:
        if not os.getenv('OPENAI_API_KEY'):raise RuntimeError('OPENAI_API_KEY not configured; agentic insights are unavailable')
        from openai import OpenAI
        client=OpenAI(api_key=os.environ['OPENAI_API_KEY'],timeout=25,max_retries=1)
    # Descriptive data, not raw diary images or medication data, to minimise disclosure.
    summary=compute_summary(readings,tasks)
    evidence={'total_readings':summary['total_readings'],'by_occasion':summary['summary_by_occasion'],'missing_due':summary['missing_due'],'data_quality_note':summary['data_quality_note']}
    run=AgentRun(user_id=user.id,started_at=datetime.now(timezone.utc).isoformat(),model_name=model,result='{}',status='running');db.add(run);db.commit()
    try:
        record(db,run,'EvidenceAgent',1,'completed',evidence)
        pattern=llm_json(client,model,'Role: PatternAgent. Identify only mathematical, supportable patterns. Return JSON with key findings (array of strings) and limitations (array). All claims must match provided measurements; avoid causes.',evidence)
        record(db,run,'PatternAgent',2,'completed',pattern)
        explanation=llm_json(client,model,'Role: ExplanationAgent. Explain the supplied observations in calm plain English. No diagnoses, treatment, targets, or causes. Return JSON with key summary (string) and questions_for_clinician (array).',{'evidence':evidence,'patterns':pattern})
        record(db,run,'ExplanationAgent',3,'completed',explanation)
        review=llm_json(client,model,'Role: SafetyReviewAgent. Independent safety check. Reject invented values, medical recommendations, diagnosis, causal inference, and unwarranted reassurance. Return JSON keys approved (boolean) and reason (string). Approve only if fully supported.',{'evidence':evidence,'pattern':pattern,'explanation':explanation})
        approved=(review.get('approved') is True and not unsafe(json.dumps(explanation)) and not unsafe(json.dumps(pattern)))
        record(db,run,'SafetyReviewAgent',4,'completed',{'approved':approved,'reason':str(review.get('reason',''))[:450]})
        if not approved:
            outcome={'approved':False,'message':'AI explanation was held for safety review. Your numerical summaries remain available.','evidence':evidence}
            run.status='held'
        else:
            outcome={'approved':True,'patterns':pattern,'explanation':explanation,'evidence':evidence};run.status='completed'
        run.result=json.dumps(outcome,ensure_ascii=False);db.commit()
        return {'run_id':run.id,'status':run.status,**outcome}
    except Exception as e:
        run.status='failed';run.result=json.dumps({'error_type':type(e).__name__});db.commit()
        raise RuntimeError('AI agent execution failed: '+type(e).__name__) from e
