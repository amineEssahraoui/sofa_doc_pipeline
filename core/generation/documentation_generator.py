
from datetime import datetime, timezone

from config.settings import (
    RAG_ENABLED,
    RAG_SECTIONS,
    GENERAL_COLLECTION,
    GENERAL_TOP_K,
    COMPONENT_TOP_K,
)

from config.llm_settings import get_llm_settings

from config.prompts import (
    build_section_messages,
    build_retrieval_queries,
)

from core.evidence.evidence_selector import build_overview_evidence, build_architecture_evidence, build_data_fields_evidence, build_mathematical_evidence, build_internal_execution_evidence
from core.evidence.evidence_selector import build_diagnostics_usage_evidence
from core.evidence.evidence_formatter import build_documentation_payload

from core.rag.retriever import retrieve_context, retrieve_chunks

from core.llm.ollama_client import generate_with_ollama
from core.llm.groq_client import generate_with_groq

def prepare_documentation_section(
    component,
    evidence_pack,
    section="overview",
):
    """
    Prepare section-specific evidence, scientific
    context and LLM messages.
    """

    if not isinstance(evidence_pack, dict):
        raise TypeError("Evidence Pack must be a dictionary")

    if evidence_pack.get("component") != component:
        raise ValueError("Evidence Pack component mismatch")

    # Select section-specific SOFA evidence

    if section == "overview":

        evidence_payload = build_overview_evidence(
            evidence_pack
        )

    elif section == "architecture":

        evidence_payload = build_architecture_evidence(
            evidence_pack
        )
    
    elif section == "data_fields":

        evidence_payload = build_data_fields_evidence(
            evidence_pack
        )

    elif section == "mathematical_formulation":

        evidence_payload = build_mathematical_evidence(
            evidence_pack
        )

    elif section == "internal_execution":

        evidence_payload = build_internal_execution_evidence(
            evidence_pack
        )
        
    elif section == "diagnostics_usage":

        evidence_payload = build_diagnostics_usage_evidence(
            evidence_pack
        )

    else:

        evidence_payload = build_documentation_payload(
            evidence_pack
        )

    # Retrieve section-specific scientific context

    retrieval_queries = []
    retrieved_context = None

    rag_active = RAG_ENABLED and section in RAG_SECTIONS

    if rag_active:

        retrieval_queries = build_retrieval_queries(
            section=section,
            component=component,
        )

        if section == "architecture":

            general_chunks = retrieve_chunks(
                collection_name=GENERAL_COLLECTION,
                queries=retrieval_queries,
                top_k=GENERAL_TOP_K,
            )

            retrieved_context = {
                "component": component,
                "general": general_chunks,
                "component_specific": [],
            }

        elif section == "mathematical_formulation":

            retrieved_context = {
                "component": component,
                "general": [],
                "component_specific": retrieve_chunks(
                    collection_name=component,
                    queries=retrieval_queries,
                    top_k=COMPONENT_TOP_K,
                ),
            }

        else:

            retrieved_context = retrieve_context(
                component=component,
                general_queries=retrieval_queries,
                component_queries=retrieval_queries,
            )

    # Build final LLM messages

    messages = build_section_messages(
        section=section,
        component=component,
        evidence=evidence_payload,
        retrieved_context=retrieved_context,
    )

    return {
        "component": component,
        "section": section,
        "evidence_payload": evidence_payload,
        "rag_active": rag_active,
        "retrieval_queries": retrieval_queries,
        "retrieved_context": retrieved_context,
        "system_prompt": messages[0]["content"],
        "user_prompt": messages[1]["content"],
        "messages": messages,
    }

def generate_documentation_section(
    component,
    evidence_pack,
    section="overview",
    provider=None,
):
    """
    Generate one documentation section using Groq or Ollama.
    """

    settings = get_llm_settings(provider)

    preparation_started_at = datetime.now(timezone.utc)

    prepared = prepare_documentation_section(
        component=component,
        evidence_pack=evidence_pack,
        section=section,
    )

    started_at = datetime.now(timezone.utc)

    if settings.provider == "groq":

        llm_result = generate_with_groq(
            messages=prepared["messages"],
            settings=settings,
        )

    elif settings.provider == "ollama":

        llm_result = generate_with_ollama(
            messages=prepared["messages"],
            settings=settings,
        )

    else:

        raise ValueError(
            f"Unsupported provider: {settings.provider}"
        )

    finished_at = datetime.now(timezone.utc)

    generated_text = llm_result.get("content") or ""

    context = prepared["retrieved_context"] or {}

    metadata = {
        "component": component,
        "section": section,
        "provider": llm_result["provider"],
        "requested_model": settings.model,
        "response_model": llm_result["model"],
        "temperature": settings.temperature,
        "max_output_tokens": settings.max_output_tokens,
        "finish_reason": llm_result["finish_reason"],
        "usage": llm_result["usage"],
        "parameters": llm_result["parameters"],

        # RAG metadata

        "rag_active": prepared["rag_active"],
        "retrieval_queries": prepared["retrieval_queries"],
        "general_chunks": len(context.get("general", [])),
        "component_chunks": len(
            context.get("component_specific", [])
        ),

        # Execution metadata

        "prompt_characters": len(prepared["user_prompt"]),
        "output_characters": len(generated_text),

        "started_at_utc": started_at.isoformat(),
        "finished_at_utc": finished_at.isoformat(),

        "preparation_seconds": (
            started_at - preparation_started_at
        ).total_seconds(),

        "elapsed_seconds": (
            finished_at - started_at
        ).total_seconds(),

        "total_elapsed_seconds": (
            finished_at - preparation_started_at
        ).total_seconds(),
    }

    return {
        "component": component,
        "section": section,
        "generated_text": generated_text,
        "llm_result": llm_result,
        "metadata": metadata,
        "prepared": prepared,
    }
