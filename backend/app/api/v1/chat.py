import json
import time
import uuid
import io
from typing import List, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.core.database import get_db, AsyncSessionLocal
from app.core.security import get_current_user_id, get_current_user_role, decode_access_token
from app.core.redis import cache_manager
from app.core.guardrails import guardrails
from app.models.conversation import Conversation, Message
from app.models.analytics import AnalyticsLog, Feedback
from app.schemas.chat import ChatRequest, ChatResponse, ConversationOut, MessageOut, FeedbackCreate, Citation
from app.services.llm_service import llm_service
from app.services.rag_service import rag_service
from app.services.agent_service import agent_orchestrator
from app.services.multi_agent import multi_agent_orchestrator, planner_agent
from app.services.memory_service import memory_manager
from app.core.telemetry import tracer
import logging

logger = logging.getLogger("NexusAI-ChatAPI")
router = APIRouter(prefix="/chat", tags=["Chat"])

@router.websocket("/ws/{session_id}")
async def websocket_chat_endpoint(websocket: WebSocket, session_id: str):
    """
    Real-time streaming WebSocket endpoint.
    Handles agentic tool execution, RAG injection, token streaming, and telemetry.
    """
    await websocket.accept()
    logger.info(f"WebSocket client connected to session: {session_id}")

    try:
        while True:
            raw_data = await websocket.receive_text()
            data = json.loads(raw_data)
            user_text = data.get("message", "").strip()
            token = data.get("token")
            model_name = data.get("model", "nexus-llama3-8b-v1")
            use_rag = data.get("use_rag", True)
            use_tools = data.get("use_tools", True)

            # Determine user_id and user_role
            user_id = "guest_user"
            user_role = "viewer"
            if token:
                payload = decode_access_token(token)
                if payload and "sub" in payload:
                    user_id = payload["sub"]
                    user_role = payload.get("role", "viewer")
            else:
                user_role = "viewer"

            # 1. Rate Limiting Check
            if await cache_manager.is_rate_limited(user_id, max_requests=60, window_seconds=60):
                await websocket.send_json({
                    "type": "error",
                    "content": "Rate limit exceeded. Please wait a moment before sending more queries."
                })
                continue

            # 2. Guardrails Inspection
            is_safe, reason, meta = guardrails.inspect_input(user_text)
            if not is_safe:
                await websocket.send_json({
                    "type": "error",
                    "content": f"Safety Alert: {reason}"
                })
                continue

            query_processed = meta.get("sanitized_text", user_text)
            sentiment = meta.get("sentiment", "neutral")

            # Start OpenTelemetry root trace
            with tracer.start_trace("chat_websocket", {"session_id": session_id, "user_id": user_id}) as trace:
                # Signal start of thinking state
                await websocket.send_json({
                    "type": "status",
                    "state": "thinking",
                    "message": "NexusAI is analyzing context and formulating execution plan..."
                })

                # 3. Agentic Multi-Agent Orchestration Phase
                multi_agent_outputs = []
                active_plan = None
                if use_tools:
                    with trace.span("agent_orchestration", {"tools_enabled": True}):
                        if planner_agent.is_complex_query(query_processed):
                            async for event in multi_agent_orchestrator.execute_plan_stream(query_processed, user_role=user_role):
                                event_payload = event.model_dump(exclude_none=True)
                                await websocket.send_json(event_payload)
                                if event.type == "plan_created" and event.data:
                                    active_plan = event.data.get("plan")
                                elif event.type == "agent_finish" and event.output:
                                    multi_agent_outputs.append(f"[{event.agent or 'Agent'}]:\n{event.output}")
                        else:
                            tool_plan = agent_orchestrator.detect_tool_need(query_processed)
                            if tool_plan:
                                tool_name = tool_plan["tool"]
                                tool_input = tool_plan["input"]
                                await websocket.send_json({
                                    "type": "tool_call",
                                    "tool": tool_name,
                                    "input": tool_input,
                                    "reason": tool_plan["reason"]
                                })
                                exec_result = await agent_orchestrator.execute_tool(tool_name, tool_input, user_role=user_role)
                                multi_agent_outputs.append(f"Tool {tool_name} output: {exec_result['output']}")
                                await websocket.send_json({
                                    "type": "tool_result",
                                    "tool": tool_name,
                                    "output": exec_result["output"],
                                    "data": exec_result.get("structured_data")
                                })

                # 4. RAG Retrieval Phase
                citations = []
                context_chunks = []
                if use_rag:
                    with trace.span("rag_retrieval", {"rag_enabled": True}):
                        await websocket.send_json({
                            "type": "status",
                            "state": "thinking",
                            "message": "Querying local domain vector database..."
                        })
                        if not rag_service.chunks:
                            rag_service.index_documents()
                        citations = rag_service.retrieve(query_processed, top_k=3)
                        context_chunks = [f"Source [{c.source}]: {c.snippet}" for c in citations]

                # 5. Build Context Messages
                memory_manager.add_message(session_id, "user", query_processed)
                context_history = memory_manager.get_prompt_context(session_id, max_messages=6)

                system_instruction = (
                    "You are NexusAI, an elite Enterprise Cloud and AI DevOps Principal Architect. "
                    "Always give concise, production-ready, security-hardened guidance."
                )
                if context_chunks:
                    system_instruction += "\n\nVerified Knowledge Base Documents:\n" + "\n".join(context_chunks)
                if multi_agent_outputs:
                    agent_str = "\n\n".join(multi_agent_outputs)
                    system_instruction += f"\n\nDynamic Specialized Agent Outputs:\n{agent_str}"

                messages = [{"role": "system", "content": system_instruction}] + context_history

                # 6. Stream Response Tokens
                await websocket.send_json({
                    "type": "status",
                    "state": "speaking",
                    "message": "Streaming response tokens..."
                })

                start_time = time.time()
                full_response = []
                token_count = 0

                with trace.span("llm_inference", {"model": model_name}):
                    async for token_chunk in llm_service.stream_chat_completion(
                        messages=messages,
                        model_name=model_name,
                        context_chunks=context_chunks
                    ):
                        full_response.append(token_chunk)
                        token_count += 1
                        await websocket.send_json({
                            "type": "token",
                            "content": token_chunk
                        })

                total_text = "".join(full_response)
                latency_ms = round((time.time() - start_time) * 1000, 1)
                confidence = guardrails.calculate_confidence(total_text, context_chunks)
                follow_ups = guardrails.generate_follow_up_suggestions(query_processed, total_text)

                memory_manager.add_message(session_id, "assistant", total_text)

                # Persist to database asynchronously
                msg_id = str(uuid.uuid4())
                try:
                    async with AsyncSessionLocal() as db:
                        # Find or create conversation
                        conv = await db.get(Conversation, session_id)
                        if not conv:
                            conv = Conversation(
                                id=session_id,
                                user_id=user_id if user_id != "guest_user" else None,
                                title=query_processed[:50] + ("..." if len(query_processed) > 50 else "")
                            )
                            db.add(conv)
                            await db.flush()

                        # Save user message
                        db.add(Message(
                            conversation_id=session_id,
                            role="user",
                            content=query_processed,
                            sentiment=sentiment
                        ))
                        # Save assistant message
                        db.add(Message(
                            id=msg_id,
                            conversation_id=session_id,
                            role="assistant",
                            content=total_text,
                            confidence_score=confidence,
                            model_name=model_name,
                            tokens_used=token_count
                        ))
                        # Log analytics
                        db.add(AnalyticsLog(
                            endpoint="websocket_chat",
                            query_snippet=query_processed[:100],
                            latency_ms=latency_ms,
                            tokens_generated=token_count,
                            model_name=model_name,
                            user_id=user_id if user_id != "guest_user" else None
                        ))
                        await db.commit()
                except Exception as e:
                    logger.error(f"Error persisting chat record: {e}")

                # 7. Final Message Payload with Trace Metadata
                done_payload = {
                    "type": "done",
                    "message_id": msg_id,
                    "confidence_score": confidence,
                    "latency_ms": latency_ms,
                    "tokens_generated": token_count,
                    "citations": [c.model_dump() for c in citations],
                    "follow_ups": follow_ups,
                    "trace_id": trace.trace_id,
                    "traceparent": trace.traceparent,
                    "trace_spans": [s.to_dict() for s in trace.spans]
                }
                if active_plan:
                    done_payload["plan"] = active_plan
                await websocket.send_json(done_payload)

    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket session error: {e}")
        try:
            await websocket.send_json({"type": "error", "content": str(e)})
        except Exception:
            pass
@router.post("/sse/{session_id}")
async def sse_chat_endpoint(
    session_id: str,
    payload: ChatRequest,
    user_id: str = Depends(get_current_user_id),
    user_role: str = Depends(get_current_user_role)
):
    """
    Server-Sent Events (SSE) streaming fallback endpoint.
    Identical streaming protocol to WebSocket, ensuring zero state loss on network downgrade.
    """
    async def sse_event_generator():
        def format_sse(event_type: str, data: Any) -> str:
            return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"

        user_text = payload.message.strip()
        model_name = payload.model_name or "nexus-llama3-8b-v1"
        use_rag = payload.use_rag if payload.use_rag is not None else True
        use_tools = payload.use_tools if payload.use_tools is not None else True

        # 1. Rate Limiting Check
        if await cache_manager.is_rate_limited(user_id, max_requests=60, window_seconds=60):
            yield format_sse("error", {"type": "error", "content": "Rate limit exceeded. Please wait a moment."})
            return

        # 2. Guardrails Inspection
        is_safe, reason, meta = guardrails.inspect_input(user_text)
        if not is_safe:
            yield format_sse("error", {"type": "error", "content": f"Safety Alert: {reason}"})
            return

        query_processed = meta.get("sanitized_text", user_text)

        with tracer.start_trace("chat_sse", {"session_id": session_id, "user_id": user_id}) as trace:
            # 3. Status - Thinking
            yield format_sse("status", {
                "type": "status",
                "state": "thinking",
                "message": "NexusAI is formulating multi-agent plan and retrieving domain architecture..."
            })

            # 4. Agentic Multi-Agent Orchestration
            multi_agent_outputs = []
            active_plan = None
            if use_tools:
                with trace.span("agent_orchestration", {"tools_enabled": True}):
                    if planner_agent.is_complex_query(query_processed):
                        async for event in multi_agent_orchestrator.execute_plan_stream(query_processed, user_role=user_role):
                            event_payload = event.model_dump(exclude_none=True)
                            yield format_sse(event.type, event_payload)
                            if event.type == "plan_created" and event.data:
                                active_plan = event.data.get("plan")
                            elif event.type == "agent_finish" and event.output:
                                multi_agent_outputs.append(f"[{event.agent or 'Agent'}]:\n{event.output}")
                    else:
                        tool_plan = agent_orchestrator.detect_tool_need(query_processed)
                        if tool_plan:
                            tool_name = tool_plan["tool"]
                            tool_input = tool_plan["input"]
                            yield format_sse("tool_call", {
                                "type": "tool_call",
                                "tool": tool_name,
                                "input": tool_input,
                                "reason": tool_plan["reason"]
                            })
                            exec_result = await agent_orchestrator.execute_tool(tool_name, tool_input, user_role=user_role)
                            multi_agent_outputs.append(f"Tool {tool_name} output: {exec_result['output']}")
                            yield format_sse("tool_result", {
                                "type": "tool_result",
                                "tool": tool_name,
                                "output": exec_result["output"],
                                "data": exec_result.get("structured_data")
                            })

            # 5. Hybrid RAG Retrieval
            citations = []
            context_chunks = []
            if use_rag:
                with trace.span("rag_retrieval", {"rag_enabled": True}):
                    if not rag_service.chunks:
                        rag_service.index_documents()
                    yield format_sse("status", {
                        "type": "status",
                        "state": "thinking",
                        "message": "Querying local domain vector database..."
                    })
                    citations = rag_service.retrieve(query_processed, top_k=3)
                    context_chunks = [f"Source [{c.source}]: {c.snippet}" for c in citations]

            # 6. Build Context Messages
            memory_manager.add_message(session_id, "user", query_processed)
            context_history = memory_manager.get_prompt_context(session_id, max_messages=6)

            system_instruction = (
                "You are NexusAI, an elite Enterprise Cloud and AI DevOps Principal Architect. "
                "Always give concise, production-ready, security-hardened guidance."
            )
            if context_chunks:
                system_instruction += "\n\nVerified Knowledge Base Documents:\n" + "\n".join(context_chunks)
            if multi_agent_outputs:
                agent_str = "\n\n".join(multi_agent_outputs)
                system_instruction += f"\n\nDynamic Specialized Agent Outputs:\n{agent_str}"

            messages = [{"role": "system", "content": system_instruction}] + context_history

            # 7. Status - Speaking & Token Streaming
            yield format_sse("status", {
                "type": "status",
                "state": "speaking",
                "message": "Streaming response tokens via SSE..."
            })

            start_time = time.time()
            full_response = []
            token_count = 0

            with trace.span("llm_inference", {"model": model_name}):
                async for token_chunk in llm_service.stream_chat_completion(
                    messages=messages,
                    model_name=model_name,
                    context_chunks=context_chunks
                ):
                    full_response.append(token_chunk)
                    token_count += 1
                    yield format_sse("token", {
                        "type": "token",
                        "content": token_chunk
                    })

            total_text = "".join(full_response)
            latency_ms = round((time.time() - start_time) * 1000, 1)
            confidence = guardrails.calculate_confidence(total_text, context_chunks)
            follow_ups = guardrails.generate_follow_up_suggestions(query_processed, total_text)

            memory_manager.add_message(session_id, "assistant", total_text)

            # 8. Persist to DB asynchronously
            msg_id = str(uuid.uuid4())
            try:
                async with AsyncSessionLocal() as db:
                    conv = await db.get(Conversation, session_id)
                    if not conv:
                        conv = Conversation(
                            id=session_id,
                            user_id=user_id if user_id != "guest_user" else None,
                            title=query_processed[:50] + ("..." if len(query_processed) > 50 else "")
                        )
                        db.add(conv)
                        await db.flush()

                    db.add(Message(conversation_id=session_id, role="user", content=query_processed))
                    db.add(Message(
                        id=msg_id,
                        conversation_id=session_id,
                        role="assistant",
                        content=total_text,
                        confidence_score=confidence,
                        model_name=model_name
                    ))
                    await db.commit()
            except Exception as db_err:
                logger.warning(f"Database persistence warning in SSE stream: {db_err}")

            # 9. Done Event with Distributed Trace Spans
            citations_payload = [c.model_dump() for c in citations]
            yield format_sse("done", {
                "type": "done",
                "message_id": msg_id,
                "citations": citations_payload,
                "follow_ups": follow_ups,
                "confidence_score": confidence,
                "latency_ms": latency_ms,
                "tokens_generated": token_count,
                "plan": active_plan,
                "transport": "sse",
                "trace_id": trace.trace_id,
                "traceparent": trace.traceparent,
                "trace_spans": [s.to_dict() for s in trace.spans]
            })

    return StreamingResponse(
        sse_event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@router.post("", response_model=ChatResponse)
async def chat_http_endpoint(
    payload: ChatRequest,
    response: Response,
    user_id: str = Depends(get_current_user_id),
    user_role: str = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db)
):
    """HTTP fallback endpoint for standard synchronous chat completion with tracing."""
    session_id = payload.conversation_id or str(uuid.uuid4())
    start_time = time.time()

    with tracer.start_trace("chat_http", {"session_id": session_id, "user_id": user_id}) as trace:
        # Set W3C Trace headers on HTTP response
        response.headers["X-Trace-ID"] = trace.trace_id
        response.headers["traceparent"] = trace.traceparent

        # RAG
        citations = []
        context_chunks = []
        if payload.use_rag:
            with trace.span("rag_retrieval", {"rag_enabled": True}):
                if not rag_service.chunks:
                    rag_service.index_documents()
                citations = rag_service.retrieve(payload.message, top_k=3)
                context_chunks = [f"[{c.source}]: {c.snippet}" for c in citations]

        memory_manager.add_message(session_id, "user", payload.message)
        context_history = memory_manager.get_prompt_context(session_id)
        messages = [{"role": "system", "content": "You are NexusAI Cloud Principal Architect."}] + context_history

        chunks = []
        with trace.span("llm_inference", {"model": payload.model_name}):
            async for chunk in llm_service.stream_chat_completion(messages, model_name=payload.model_name):
                chunks.append(chunk)

        total_text = "".join(chunks)
        latency = round((time.time() - start_time) * 1000, 1)
        confidence = guardrails.calculate_confidence(total_text, context_chunks)
        follow_ups = guardrails.generate_follow_up_suggestions(payload.message, total_text)

        # Persist
        conv = await db.get(Conversation, session_id)
        if not conv:
            conv = Conversation(id=session_id, user_id=user_id if user_id != "guest_user" else None, title=payload.message[:50])
            db.add(conv)
            await db.flush()

        msg_id = str(uuid.uuid4())
        db.add(Message(conversation_id=session_id, role="user", content=payload.message))
        db.add(Message(id=msg_id, conversation_id=session_id, role="assistant", content=total_text, confidence_score=confidence, model_name=payload.model_name))
        await db.commit()

        return ChatResponse(
            message_id=msg_id,
            conversation_id=session_id,
            content=total_text,
            confidence_score=confidence,
            model_name=payload.model_name,
            follow_ups=follow_ups,
            citations=citations,
            latency_ms=latency,
            tokens_generated=len(chunks),
            trace_id=trace.trace_id,
            traceparent=trace.traceparent,
            trace_spans=[s.to_dict() for s in trace.spans]
        )

@router.get("/conversations", response_model=List[ConversationOut])
async def list_conversations(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Retrieves past conversation sessions for the current user."""
    stmt = select(Conversation).order_by(desc(Conversation.updated_at)).limit(50)
    if user_id != "guest_user":
        stmt = stmt.where(Conversation.user_id == user_id)
    result = await db.execute(stmt)
    conversations = result.scalars().all()
    return [ConversationOut.model_validate(c) for c in conversations]

@router.get("/conversations/{conversation_id}", response_model=ConversationOut)
async def get_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Returns conversation and all message turns."""
    conv = await db.get(Conversation, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Load messages
    stmt = select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at)
    res = await db.execute(stmt)
    messages = res.scalars().all()
    
    out = ConversationOut.model_validate(conv)
    out.messages = [MessageOut.model_validate(m) for m in messages]
    return out

@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db)
):
    conv = await db.get(Conversation, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    await db.delete(conv)
    await db.commit()
    memory_manager.clear(conversation_id)
    return {"message": "Conversation deleted successfully"}

@router.post("/feedback")
async def submit_feedback(
    payload: FeedbackCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Submits user feedback (thumbs up/down) linked to conversation quality scoring."""
    feedback = Feedback(
        message_id=payload.message_id,
        rating=payload.rating,
        comment=payload.comment,
        user_id=user_id if user_id != "guest_user" else None
    )
    db.add(feedback)
    await db.commit()
    return {"status": "success", "message": "Feedback recorded. Thank you for rating this response!"}

@router.get("/export/{conversation_id}")
async def export_conversation(
    conversation_id: str,
    format: str = Query("text", pattern="^(text|pdf)$"),
    db: AsyncSession = Depends(get_db)
):
    """Exports conversation as Plain Text or PDF document."""
    conv = await db.get(Conversation, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    stmt = select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at)
    messages = (await db.execute(stmt)).scalars().all()

    if format == "text":
        lines = [f"=== NEXUS AI CHAT EXPORT ===", f"Session: {conv.title}", f"Exported: {conv.updated_at}", ""]
        for m in messages:
            lines.append(f"[{m.role.upper()}]:\n{m.content}\n")
        content = "\n".join(lines)
        return Response(
            content=content,
            media_type="text/plain",
            headers={"Content-Disposition": f"attachment; filename=chat_{conversation_id[:8]}.txt"}
        )

    # PDF Export using ReportLab
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas

        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter

        p.setFont("Helvetica-Bold", 16)
        p.drawString(50, height - 50, f"NexusAI Consultation: {conv.title[:45]}")
        p.setFont("Helvetica", 10)
        p.drawString(50, height - 70, f"Generated: {conv.updated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        p.line(50, height - 80, width - 50, height - 80)

        y = height - 105
        p.setFont("Helvetica", 10)

        for m in messages:
            role_header = f"[{m.role.upper()}]:"
            p.setFont("Helvetica-Bold", 11)
            p.drawString(50, y, role_header)
            y -= 15

            p.setFont("Helvetica", 9)
            # Simple text wrap
            words = m.content.split()
            line = []
            for w in words:
                line.append(w)
                if len(" ".join(line)) > 90:
                    p.drawString(50, y, " ".join(line))
                    y -= 12
                    line = []
                    if y < 50:
                        p.showPage()
                        y = height - 50
                        p.setFont("Helvetica", 9)
            if line:
                p.drawString(50, y, " ".join(line))
                y -= 18

            if y < 60:
                p.showPage()
                y = height - 50

        p.save()
        buffer.seek(0)
        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=chat_{conversation_id[:8]}.pdf"}
        )
    except Exception as e:
        logger.error(f"PDF export error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {e}")
