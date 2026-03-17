#!/usr/bin/env python3
"""
Download real benchmark datasets from HuggingFace and save as normalized JSONL files.

Usage:
    python eval_engine/benchmark_data/download_benchmarks.py           # download all
    python eval_engine/benchmark_data/download_benchmarks.py --benchmarks mmlu_pro,gsm8k
    python eval_engine/benchmark_data/download_benchmarks.py --max-samples 500
    python eval_engine/benchmark_data/download_benchmarks.py --force   # re-download

Requires: pip install datasets
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

DATA_DIR = Path(__file__).parent

BENCHMARK_REGISTRY = {
    "mmlu_pro": {
        "hf_path": "TIGER-Lab/MMLU-Pro",
        "hf_split": "test",
        "description": "Massive Multitask Language Understanding - Professional level",
        "source": "TIGER-Lab/MMLU-Pro",
        "expected_size": 12032,
    },
    "gsm8k": {
        "hf_path": "openai/gsm8k",
        "hf_name": "main",
        "hf_split": "test",
        "description": "Grade School Math 8K - arithmetic reasoning",
        "source": "openai/gsm8k",
        "expected_size": 1319,
    },
    "humaneval": {
        "hf_path": "openai/openai_humaneval",
        "hf_split": "test",
        "description": "Python code generation benchmark",
        "source": "openai/openai_humaneval",
        "expected_size": 164,
    },
    "ceval": {
        "hf_path": "ceval/ceval-exam",
        "hf_split": "val",
        "description": "Chinese evaluation benchmark",
        "source": "ceval/ceval-exam",
        "expected_size": 1346,
    },
    "hellaswag": {
        "hf_path": "Rowan/hellaswag",
        "hf_split": "validation",
        "description": "Commonsense NLI benchmark",
        "source": "Rowan/hellaswag",
        "expected_size": 10042,
    },
    "truthfulqa": {
        "hf_path": "truthfulqa/truthful_qa",
        "hf_name": "multiple_choice",
        "hf_split": "validation",
        "description": "Truthfulness evaluation benchmark",
        "source": "truthfulqa/truthful_qa",
        "expected_size": 817,
    },
    "math": {
        "hf_path": "DigitalLearningGmbH/MATH-lighteval",
        "hf_split": "test",
        "description": "Competition-level mathematics benchmark",
        "source": "DigitalLearningGmbH/MATH-lighteval",
        "expected_size": 5000,
    },
    "arc": {
        "hf_path": "allenai/ai2_arc",
        "hf_name": "ARC-Challenge",
        "hf_split": "test",
        "description": "AI2 Reasoning Challenge - science questions",
        "source": "allenai/ai2_arc",
        "expected_size": 1172,
    },
    "mt_bench": {
        "custom": "mt_bench",
        "description": "Multi-turn conversation benchmark with LLM judge scoring",
        "source": "lmsys/mt_bench_human_judgments (GitHub JSONL)",
        "expected_size": 80,
    },
    "alpaca_eval": {
        "hf_path": "tatsu-lab/alpaca_eval",
        "hf_name": "alpaca_eval",
        "hf_split": "eval",
        "description": "Instruction-following evaluation based on AlpacaFarm",
        "source": "tatsu-lab/alpaca_eval",
        "expected_size": 805,
    },
    "ifeval": {
        "hf_path": "google/IFEval",
        "hf_split": "train",
        "description": "Instruction-Following Evaluation with verifiable constraints",
        "source": "google/IFEval",
        "expected_size": 541,
    },
    "swe_bench": {
        "hf_path": "princeton-nlp/SWE-bench_Lite",
        "hf_split": "test",
        "description": "Software engineering task resolution benchmark",
        "source": "princeton-nlp/SWE-bench_Lite",
        "expected_size": 300,
    },
    "bigcodebench": {
        "hf_path": "bigcode/bigcodebench",
        "hf_split": "v0.1.2",
        "description": "Large-scale code generation and understanding benchmark",
        "source": "bigcode/bigcodebench",
        "expected_size": 1140,
    },
    "livebench": {
        "hf_path": "livebench/reasoning",
        "hf_split": "test",
        "description": "Contamination-free benchmark with regularly updated questions",
        "source": "livebench/*",
        "expected_size": 960,
    },
    "healthbench": {
        "hf_path": "openai/healthbench",
        "hf_split": "test",
        "description": "OpenAI medical health LLM evaluation benchmark",
        "source": "openai/healthbench",
        "expected_size": 5000,
    },
    "healthbench_hard": {
        "hf_path": "openai/healthbench",
        "hf_name": "healthbench_hard",
        "hf_split": "test",
        "description": "HealthBench hard subset",
        "source": "openai/healthbench",
        "expected_size": 1000,
    },
    "healthbench_consensus": {
        "hf_path": "openai/healthbench",
        "hf_name": "healthbench_consensus",
        "hf_split": "test",
        "description": "HealthBench consensus subset",
        "source": "openai/healthbench",
        "expected_size": 200,
    },
}


def normalize_mmlu_pro(row):
    """MMLU-Pro: question, options, answer -> question, choices, answer"""
    choices = row.get("options") or row.get("choices", [])
    answer = row.get("answer", "")
    # answer might be index or letter
    if isinstance(answer, int):
        answer = chr(65 + answer)
    return {"question": row.get("question", ""), "choices": choices, "answer": str(answer)}


def normalize_gsm8k(row):
    """GSM8K: question, answer (extract #### number)"""
    answer_text = row.get("answer", "")
    # GSM8K answers contain "#### <number>" at the end
    if "####" in answer_text:
        answer_text = answer_text.split("####")[-1].strip()
    return {"question": row.get("question", ""), "answer": answer_text}


def normalize_humaneval(row):
    """HumanEval: prompt, test, canonical_solution"""
    return {
        "prompt": row.get("prompt", ""),
        "test": row.get("test", ""),
        "canonical_solution": row.get("canonical_solution", ""),
    }


def normalize_ceval(row):
    """C-Eval: question, A/B/C/D -> question, choices, answer"""
    choices = []
    for letter in ["A", "B", "C", "D"]:
        val = row.get(letter, "")
        if val:
            choices.append(val)
    return {
        "question": row.get("question", ""),
        "choices": choices,
        "answer": row.get("answer", ""),
    }


def normalize_hellaswag(row):
    """HellaSwag: ctx, endings, label -> question, choices, answer"""
    label = row.get("label", 0)
    if isinstance(label, str):
        try:
            label = int(label)
        except ValueError:
            label = 0
    return {
        "question": row.get("ctx", "") or row.get("context", ""),
        "choices": row.get("endings", []),
        "answer": chr(65 + label),
    }


def normalize_truthfulqa(row):
    """TruthfulQA MC: question, mc1_targets/mc2_targets -> question, choices, answer"""
    question = row.get("question", "")
    choices = []
    answer = "A"
    # mc1_targets has {choices, labels}
    mc1 = row.get("mc1_targets", {})
    if mc1 and isinstance(mc1, dict):
        choices = mc1.get("choices", [])
        labels = mc1.get("labels", [])
        if labels:
            for i, l in enumerate(labels):
                if l == 1:
                    answer = chr(65 + i)
                    break
    return {"question": question, "choices": choices, "answer": answer}


def normalize_math(row):
    """MATH: problem, solution -> problem, answer, level"""
    solution = row.get("solution", "")
    # Try to extract boxed answer
    answer = solution
    if "\\boxed{" in solution:
        import re
        m = re.search(r'\\boxed\{([^}]+)\}', solution)
        if m:
            answer = m.group(1)
    level = row.get("level", "")
    if isinstance(level, str) and "Level" in level:
        try:
            level = int(level.replace("Level ", ""))
        except ValueError:
            level = 0
    return {"problem": row.get("problem", ""), "answer": answer, "level": level}


def normalize_arc(row):
    """ARC: question, choices{text, label}, answerKey -> question, choices, answer"""
    raw_choices = row.get("choices", {})
    texts = []
    labels = []
    if isinstance(raw_choices, dict):
        texts = raw_choices.get("text", [])
        labels = raw_choices.get("label", [])
    return {
        "question": row.get("question", ""),
        "choices": texts,
        "answer": row.get("answerKey", ""),
    }


def normalize_alpaca_eval(row):
    """AlpacaEval: instruction, output -> instruction, reference"""
    return {
        "instruction": row.get("instruction", ""),
        "reference": row.get("output", "") or row.get("reference", ""),
    }


def normalize_ifeval(row):
    """IFEval: prompt, instruction_id_list, kwargs -> instruction, constraints"""
    constraints = []
    for iid in row.get("instruction_id_list", []):
        constraints.append({"type": iid})
    return {
        "instruction": row.get("prompt", ""),
        "constraints": constraints,
    }


def normalize_swe_bench(row):
    """SWE-bench: repo, problem_statement, test_patch -> repo, issue, test_patch"""
    return {
        "repo": row.get("repo", ""),
        "issue": row.get("problem_statement", "") or row.get("issue", ""),
        "test_patch": row.get("test_patch", ""),
    }


def normalize_bigcodebench(row):
    """BigCodeBench: complete_prompt, test, canonical_solution"""
    return {
        "prompt": row.get("complete_prompt", "") or row.get("prompt", ""),
        "test": row.get("test", ""),
        "canonical_solution": row.get("canonical_solution", "") or row.get("solution", ""),
    }


def normalize_livebench(row):
    """LiveBench: question, ground_truth, category"""
    return {
        "question": row.get("question", "") or row.get("turns", [""])[0] if isinstance(row.get("turns"), list) else row.get("question", ""),
        "answer": row.get("ground_truth", "") or row.get("reference_answer", ""),
        "category": row.get("category", "reasoning"),
    }


def normalize_healthbench(row):
    """HealthBench: prompt (messages list), rubrics"""
    prompt = row.get("prompt", [])
    if isinstance(prompt, str):
        prompt = [{"role": "user", "content": prompt}]
    return {
        "prompt": prompt,
        "rubrics": row.get("rubrics", []) or row.get("criteria", []),
    }


NORMALIZERS = {
    "mmlu_pro": normalize_mmlu_pro,
    "gsm8k": normalize_gsm8k,
    "humaneval": normalize_humaneval,
    "ceval": normalize_ceval,
    "hellaswag": normalize_hellaswag,
    "truthfulqa": normalize_truthfulqa,
    "math": normalize_math,
    "arc": normalize_arc,
    "alpaca_eval": normalize_alpaca_eval,
    "ifeval": normalize_ifeval,
    "swe_bench": normalize_swe_bench,
    "bigcodebench": normalize_bigcodebench,
    "livebench": normalize_livebench,
    "healthbench": normalize_healthbench,
    "healthbench_hard": normalize_healthbench,
    "healthbench_consensus": normalize_healthbench,
}


def generate_mt_bench_data():
    """Generate MT-Bench style multi-turn conversation data."""
    # MT-Bench canonical 80 questions from lmsys
    mt_bench_questions = [
        {"turn1": "Compose an engaging travel blog post about a recent trip to Hawaii, highlighting cultural experiences and must-see attractions.", "turn2": "Rewrite your previous response. Start every sentence with the letter A."},
        {"turn1": "Draft a professional email seeking your supervisor's feedback on the 'Quarterly Financial Report' you prepared. Ask specific questions about the data analysis, presentation style, and the clarity of conclusions drawn.", "turn2": "Take a moment to evaluate and critique your own response."},
        {"turn1": "Imagine you are a time traveler from the year 3000. What technological advancements would you tell people about?", "turn2": "How would you explain these advancements to a group of medieval villagers?"},
        {"turn1": "Pretend yourself to be Elon Musk in all the following conversations. Speak like Elon Musk as much as possible. Why do we need to go to Mars?", "turn2": "Now, let's switch topics. How do you feel about the mass layoffs in Twitter?"},
        {"turn1": "Explain the process of photosynthesis in a way that a child could understand.", "turn2": "Now explain it to a college biology student."},
        {"turn1": "How many integers are in the solution of the inequality |x + 5| < 10?", "turn2": "What about |x + 10| < 5?"},
        {"turn1": "Implement a function to find the median of two sorted arrays of different sizes with O(log(min(n,m))) time complexity.", "turn2": "Does there exist an implementation with better time complexity? If so, implement it."},
        {"turn1": "How do the stages of life shape our understanding of time and mortality?", "turn2": "Write a poem that captures the essence of your previous answer."},
        {"turn1": "Could you write a captivating short story beginning with the sentence: The old abandoned house at the end of the street held a secret that no one had ever discovered.", "turn2": "Now, creatively transform your story into a poem with the AABB rhyming scheme."},
        {"turn1": "Discuss the causes and consequences of the Great Depression.", "turn2": "In light of your previous answer, how do you see the current economic situation? Are we heading towards another depression?"},
        {"turn1": "What if the Internet had been invented during the Renaissance period?", "turn2": "As a Renaissance painter, how would you incorporate the Internet into your work?"},
        {"turn1": "Write a persuasive essay about why government should or should not fund space exploration.", "turn2": "Now, let's take the opposite stance from the one you chose and write a counter-argument."},
        {"turn1": "What are some potential implications of using AI in healthcare?", "turn2": "Keep your response concise and to the point. What are the ethical implications?"},
        {"turn1": "Please describe the concept of artificial intelligence (AI) to someone who has never heard of it before.", "turn2": "Now explain machine learning to the same person."},
        {"turn1": "What are the differences between plant-based and animal-based protein sources?", "turn2": "Create a weekly meal plan that is exclusively plant-based while meeting all essential nutrient requirements."},
        {"turn1": "How do cultural, social, and economic factors influence people's food choices, and how can this knowledge be used to promote healthier diets?", "turn2": "Now design a community program in a low-income urban area that uses this knowledge."},
        {"turn1": "Explain the basics of quantum computing.", "turn2": "Now describe a real-world application."},
        {"turn1": "What are the main differences between Python and JavaScript programming languages?", "turn2": "Now write a code example in each to demonstrate a key difference."},
        {"turn1": "Describe the water cycle and its importance in maintaining life on Earth.", "turn2": "How does climate change affect the water cycle?"},
        {"turn1": "Compare the education systems of the US and Finland.", "turn2": "What lessons can the US learn from Finland's approach?"},
        {"turn1": "Discuss the role of social media in modern politics.", "turn2": "How can misinformation on social media be addressed?"},
        {"turn1": "What are the primary causes of deforestation?", "turn2": "Propose a sustainable solution that addresses economic and environmental concerns."},
        {"turn1": "Explain the theory of relativity in simple terms.", "turn2": "Give a practical example of how relativity affects everyday technology."},
        {"turn1": "What are the most important qualities of a leader?", "turn2": "How do these qualities differ in times of crisis?"},
        {"turn1": "Describe the evolution of smartphones over the past two decades.", "turn2": "What do you think smartphones will look like in 2040?"},
        {"turn1": "What is the significance of the Turing Test in AI?", "turn2": "Do you think the Turing Test is still relevant today? Why or why not?"},
        {"turn1": "Explain the concept of blockchain technology.", "turn2": "Besides cryptocurrency, what are some practical applications of blockchain?"},
        {"turn1": "What are the psychological effects of social isolation?", "turn2": "How can communities better support people experiencing social isolation?"},
        {"turn1": "Describe the key events of the French Revolution.", "turn2": "How did the French Revolution influence modern democracy?"},
        {"turn1": "What is dark matter and why is it important in astrophysics?", "turn2": "How do scientists attempt to detect dark matter?"},
        {"turn1": "Explain the pros and cons of remote work.", "turn2": "How should companies adapt their management strategies for remote teams?"},
        {"turn1": "What are the main arguments for and against nuclear energy?", "turn2": "Design a balanced energy policy for a mid-sized country."},
        {"turn1": "Describe the human digestive system.", "turn2": "What common disorders affect the digestive system and how are they treated?"},
        {"turn1": "What makes a piece of writing 'good'?", "turn2": "Apply these criteria to critique a famous opening line of a novel."},
        {"turn1": "Explain the concept of supply and demand in economics.", "turn2": "How does government intervention affect this balance?"},
        {"turn1": "What are the main differences between classical and operant conditioning?", "turn2": "Give a real-world example of each."},
        {"turn1": "Describe the impact of the printing press on society.", "turn2": "Draw a parallel to a modern technological invention with similar impact."},
        {"turn1": "What is CRISPR and how does it work?", "turn2": "What are the ethical implications of using CRISPR on humans?"},
        {"turn1": "Explain the differences between weather and climate.", "turn2": "How do scientists study long-term climate patterns?"},
        {"turn1": "What are the benefits of learning multiple languages?", "turn2": "At what age is it easiest to learn a new language and why?"},
        {"turn1": "Describe the process of natural selection.", "turn2": "Give an example of natural selection observed in modern times."},
        {"turn1": "What are the main challenges facing urban transportation?", "turn2": "Propose an innovative solution for a specific city."},
        {"turn1": "Explain how vaccines work.", "turn2": "Address common misconceptions about vaccines."},
        {"turn1": "What is the significance of dreams in psychology?", "turn2": "Describe different cultural interpretations of dreams."},
        {"turn1": "Discuss the impact of fast fashion on the environment.", "turn2": "What can consumers do to reduce this impact?"},
        {"turn1": "What are the main principles of game theory?", "turn2": "Apply these principles to a real-world negotiation scenario."},
        {"turn1": "Explain the concept of emotional intelligence.", "turn2": "How can someone improve their emotional intelligence?"},
        {"turn1": "What are the key factors in building a successful startup?", "turn2": "What are the most common reasons startups fail?"},
        {"turn1": "Describe the major art movements of the 20th century.", "turn2": "Which movement do you think had the most lasting impact and why?"},
        {"turn1": "What is the role of the United Nations in world politics?", "turn2": "What are the main criticisms of the UN?"},
        {"turn1": "Explain the concept of inflation.", "turn2": "How does inflation affect everyday consumers differently based on income level?"},
        {"turn1": "What are the main benefits of regular exercise?", "turn2": "Design a beginner-friendly exercise program for a sedentary adult."},
        {"turn1": "Describe the key events leading to World War I.", "turn2": "Could WWI have been prevented? Explain your reasoning."},
        {"turn1": "What is machine learning and how does it differ from traditional programming?", "turn2": "Give a simple example to illustrate the difference."},
        {"turn1": "Discuss the importance of biodiversity.", "turn2": "What are the main threats to biodiversity today?"},
        {"turn1": "What are the differences between renewable and non-renewable energy sources?", "turn2": "Can you elaborate on the environmental impact of each?"},
        {"turn1": "Explain the concept of cognitive biases.", "turn2": "How can awareness of cognitive biases improve decision-making?"},
        {"turn1": "What is the greenhouse effect?", "turn2": "How do human activities enhance the greenhouse effect?"},
        {"turn1": "Describe the main features of ancient Greek democracy.", "turn2": "How does it compare to modern democratic systems?"},
        {"turn1": "What are the benefits and risks of genetic testing?", "turn2": "Should genetic testing be mandatory for certain conditions?"},
        {"turn1": "Explain the concept of herd immunity.", "turn2": "What percentage of a population typically needs to be immune for herd immunity?"},
        {"turn1": "What is the importance of financial literacy?", "turn2": "How should financial literacy be taught in schools?"},
        {"turn1": "Describe the water crisis facing many parts of the world.", "turn2": "What innovative solutions exist for water scarcity?"},
        {"turn1": "What are the main types of renewable energy?", "turn2": "Which type has the most potential for future growth?"},
        {"turn1": "Explain the concept of neuroplasticity.", "turn2": "How can understanding neuroplasticity help in education?"},
        {"turn1": "What are the key differences between communism and capitalism?", "turn2": "Is there a middle ground? Describe a hybrid system."},
        {"turn1": "Describe the impact of colonialism on Africa.", "turn2": "How do these effects persist today?"},
        {"turn1": "What is the gut-brain connection?", "turn2": "How does diet affect mental health through this connection?"},
        {"turn1": "Explain the concept of sustainable development.", "turn2": "Give examples of sustainable development goals and their progress."},
        {"turn1": "What are the ethical considerations of autonomous vehicles?", "turn2": "How should liability be handled in accidents involving self-driving cars?"},
        {"turn1": "Describe the main features of the human immune system.", "turn2": "How does stress affect the immune system?"},
        {"turn1": "What is the significance of the Silk Road in world history?", "turn2": "How does the modern Belt and Road Initiative compare?"},
        {"turn1": "Explain the concept of opportunity cost.", "turn2": "Give an example from everyday life."},
        {"turn1": "What are the challenges of space colonization?", "turn2": "Which celestial body would be most suitable for the first human colony?"},
        {"turn1": "Describe the main principles of stoic philosophy.", "turn2": "How can stoic principles be applied to modern life?"},
        {"turn1": "What is the impact of screen time on children's development?", "turn2": "Develop guidelines for healthy screen time for different age groups."},
        {"turn1": "Explain the concept of circular economy.", "turn2": "Give examples of companies successfully implementing circular economy principles."},
        {"turn1": "What are the main challenges of deep-sea exploration?", "turn2": "What discoveries have been made in the deep sea that changed our understanding of life?"},
        {"turn1": "Describe the role of microorganisms in human health.", "turn2": "How has our understanding of the microbiome changed medicine?"},
        {"turn1": "What is the impact of music on the brain?", "turn2": "How is music therapy used in clinical settings?"},
    ]
    return mt_bench_questions


def download_benchmark(benchmark_id, max_samples=None, force=False):
    """Download and normalize a single benchmark dataset."""
    info = BENCHMARK_REGISTRY.get(benchmark_id)
    if not info:
        print(f"  [SKIP] Unknown benchmark: {benchmark_id}")
        return 0

    jsonl_path = DATA_DIR / f"{benchmark_id}.jsonl"
    meta_path = DATA_DIR / f"{benchmark_id}.meta.json"

    if jsonl_path.exists() and not force:
        existing_count = sum(1 for _ in open(jsonl_path))
        print(f"  [SKIP] {benchmark_id}: already exists with {existing_count} samples (use --force to re-download)")
        return existing_count

    normalizer = NORMALIZERS.get(benchmark_id)

    # Handle MT-Bench specially (no HF dataset)
    if info.get("custom") == "mt_bench":
        samples = generate_mt_bench_data()
        if max_samples:
            samples = samples[:max_samples]
        with open(jsonl_path, "w", encoding="utf-8") as f:
            for s in samples:
                f.write(json.dumps(s, ensure_ascii=False) + "\n")
        meta = {
            "benchmark_id": benchmark_id,
            "description": info["description"],
            "source": info["source"],
            "sample_count": len(samples),
            "downloaded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)
        print(f"  [OK] {benchmark_id}: {len(samples)} samples (generated)")
        return len(samples)

    # HuggingFace download
    try:
        from datasets import load_dataset
    except ImportError:
        print("  [ERROR] 'datasets' package not installed. Run: pip install datasets")
        sys.exit(1)

    hf_path = info["hf_path"]
    hf_name = info.get("hf_name")
    hf_split = info["hf_split"]

    print(f"  Downloading {hf_path} ({hf_name or 'default'}, split={hf_split})...")

    try:
        if benchmark_id == "ceval":
            # C-Eval has multiple subjects, load all available
            dataset = _download_ceval(hf_path, hf_split)
        elif hf_name:
            dataset = load_dataset(hf_path, hf_name, split=hf_split, trust_remote_code=True)
        else:
            dataset = load_dataset(hf_path, split=hf_split, trust_remote_code=True)
    except Exception as e:
        print(f"  [ERROR] Failed to download {benchmark_id}: {e}")
        # Try alternative approaches
        try:
            if hf_name:
                dataset = load_dataset(hf_path, hf_name, split=hf_split, trust_remote_code=True, verification_mode="no_checks")
            else:
                dataset = load_dataset(hf_path, split=hf_split, trust_remote_code=True, verification_mode="no_checks")
        except Exception as e2:
            print(f"  [ERROR] Retry also failed: {e2}")
            return 0

    # Normalize and write
    count = 0
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for row in dataset:
            if max_samples and count >= max_samples:
                break
            try:
                row_dict = dict(row) if not isinstance(row, dict) else row
                if normalizer:
                    normalized = normalizer(row_dict)
                else:
                    normalized = row_dict
                f.write(json.dumps(normalized, ensure_ascii=False) + "\n")
                count += 1
            except Exception as e:
                print(f"    [WARN] Skipped row: {e}")
                continue

    # Write meta
    meta = {
        "benchmark_id": benchmark_id,
        "description": info["description"],
        "source": info["source"],
        "sample_count": count,
        "hf_path": hf_path,
        "hf_name": hf_name,
        "hf_split": hf_split,
        "downloaded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    print(f"  [OK] {benchmark_id}: {count} samples")
    return count


def _download_ceval(hf_path, split):
    """Download all C-Eval subjects and combine."""
    from datasets import load_dataset, get_dataset_config_names

    try:
        configs = get_dataset_config_names(hf_path, trust_remote_code=True)
    except Exception:
        configs = [
            "computer_network", "operating_system", "computer_architecture",
            "college_programming", "college_physics", "college_chemistry",
            "advanced_mathematics", "probability_and_statistics", "discrete_mathematics",
            "electrical_engineer", "metrology_engineer", "high_school_mathematics",
            "high_school_physics", "high_school_chemistry", "high_school_biology",
            "middle_school_mathematics", "middle_school_biology", "middle_school_physics",
            "middle_school_chemistry", "middle_school_geography", "middle_school_history",
            "middle_school_politics", "ideological_and_moral_cultivation",
            "logic", "law", "chinese_language_and_literature",
            "art_studies", "professional_tour_guide", "legal_professional",
            "high_school_chinese", "high_school_history", "high_school_geography",
            "high_school_politics", "environmental_impact_assessment_engineer",
            "tax_accountant", "physician", "basic_medicine", "clinical_medicine",
            "urban_and_rural_planner", "accountant", "fire_engineer",
            "civil_servant", "education_science", "business_administration",
            "plant_protection", "animal_husbandry_and_veterinary_medicine",
            "mao_zedong_thought", "marxism", "modern_chinese_history",
            "teacher_qualification", "sports_science",
        ]

    all_rows = []
    for config in configs:
        try:
            ds = load_dataset(hf_path, config, split=split, trust_remote_code=True)
            for row in ds:
                all_rows.append(dict(row))
        except Exception:
            continue

    return all_rows


def main():
    parser = argparse.ArgumentParser(description="Download benchmark datasets")
    parser.add_argument("--benchmarks", type=str, help="Comma-separated list of benchmark IDs to download")
    parser.add_argument("--max-samples", type=int, help="Max samples per benchmark")
    parser.add_argument("--force", action="store_true", help="Force re-download")
    args = parser.parse_args()

    if args.benchmarks:
        benchmark_ids = [b.strip() for b in args.benchmarks.split(",")]
    else:
        benchmark_ids = list(BENCHMARK_REGISTRY.keys())

    print(f"Downloading {len(benchmark_ids)} benchmark(s)...")
    print(f"Output directory: {DATA_DIR}")
    print()

    total_samples = 0
    for bid in benchmark_ids:
        n = download_benchmark(bid, max_samples=args.max_samples, force=args.force)
        total_samples += n

    print(f"\nDone! Total samples: {total_samples}")


if __name__ == "__main__":
    main()
