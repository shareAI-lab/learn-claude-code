# RZ Experiments

Various experiments for inside out understanding of coding agent design and implementation

## Repo management

### setup up uptream to the source https://github.com/shareAI-lab/learn-claude-code.git in github

```
git remote add upstream https://github.com/shareAI-lab/learn-claude-code.git
git fetch upstream
```

### Repo branch for experiment and manage the code sync with original upstream

```
git checkout -b rz_experiment
```

## What to experiments

### Use fully AI-native software development approach for the experiments

- Create plan custom agent with what to experiment to generate a experiment plan agent
- Use low cost model to generate the experiment plan and use high end model to critize and enhance the experiment plan
- Assign the implementation changes and testing to the experiment plan agent for it to finish the task fully without intervention
- Use high cost model

### learn-claude-code code base experiments

Question: How agent manage agent skills and how agent decide which skill to inovke and with what information made available to agent skill or the full conext?


