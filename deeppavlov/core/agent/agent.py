from collections import defaultdict
from typing import List

from deeppavlov.core.models.component import Component
from deeppavlov.core.skill.skill import Skill
from deeppavlov.agents.default_agent import TransparentFilter, HighestConfidenceSelector


class Agent(Component):
    def __init__(self, skills: List[Skill], skills_processor=None, skills_filter=None, *args, **kwargs):
        self.skills = skills
        self.skills_filter = skills_filter or TransparentFilter(len(skills))
        self.skills_processor = skills_processor or HighestConfidenceSelector()
        self.history = defaultdict(list)
        self.states = defaultdict(lambda: [None] * len(self.skills))

    def __call__(self, utterances, ids=None):
        batch_size = len(utterances)
        ids = ids or list(range(batch_size))
        batch_history = [self.history[id] for id in ids]
        batch_states = [self.states[id] for id in ids]
        filtered = self.skills_filter(utterances, batch_history)
        responses = []
        for skill_i, (m, skill) in enumerate(zip(zip(*filtered), self.skills)):
            m = [i for i, m in enumerate(m) if m]
            # TODO: utterances, batch_history and batch_states batches should be lists, not tuples
            batch = tuple(zip(*[(utterances[i], batch_history[i], batch_states[i][skill_i]) for i in m]))
            res = [(None, 0.)] * batch_size
            if batch:
                predicted, confidence, *state = skill(*batch)
                state = state[0] if state else [None] * len(predicted)
                for i, predicted, confidence, state in zip(m, predicted, confidence, state):
                    res[i] = (predicted, confidence)
                    batch_states[i][skill_i] = state
            responses.append(res)
        responses = self.skills_processor(utterances, batch_history, *responses)
        for history, utterance, response in zip(batch_history, utterances, responses):
            history.append(utterance)
            history.append(response)
        return responses
