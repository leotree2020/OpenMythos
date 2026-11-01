# Fixed first-pass continuations — all 12 preserved

Experiment: MYTHOS-CPU-INFERENCE-V1. Engineering PASS; frozen quality screen FAIL (0/12 joint, required 9/12).
These are exactly the first pass, not selected samples. No EOS occurred: each effective continuation contains all 64 raw new tokens.
Seed=731000+ID, greedy, depth8, no cache. Repetition counts use token 4-grams, not words.

## Prompt 1

Seed: 731001; automatic: FAIL; maximum 4-gram count: 3; coherent: True.

Prompt:
````text
The capital of France is
````

Exact continuation:
````text
 Paris. It is the capital of the French Republic, the largest country in Europe, and the largest city in the world. It is the capital of the French Republic, the largest country in the world, and the largest city in the world. It is the capital of the French Republic, the largest country in the world
````

承接首都提示，语言可理解，但后半段机械重复。

首词 Paris 合理；最大国家和世界最大城市的断言混淆或错误，未作为事实能力验收。

## Prompt 2

Seed: 731002; automatic: FAIL; maximum 4-gram count: 5; coherent: True.

Prompt:
````text
In 1969, the first humans landed on the Moon. The mission was called
````

Exact continuation:
````text
 Apollo 11. The first human to land on the Moon was Neil Armstrong. He was the first person to walk on the Moon. He was the first person to walk on the Moon. He was the first person to walk on the Moon. He was the first person to walk on the Moon. He was the first
````

任务名称与人物说明承接提示，随后重复同一句话。

Apollo 11 和 Neil Armstrong 的核心提法合理；未开展独立事实基准评测。

## Prompt 3

Seed: 731003; automatic: FAIL; maximum 4-gram count: 3; coherent: True.

Prompt:
````text
Photosynthesis is the process by which plants
````

Exact continuation:
````text
 and animals convert light energy into chemical energy. It is the process by which plants and animals convert carbon dioxide into glucose and oxygen. The process is also known as photosynthesis. Photosynthesis is the process by which plants and animals convert carbon dioxide into glucose and oxygen. Photosynthesis is the process by which plants and animals convert carbon
````

围绕光合作用，语言结构可理解，定义反复重复。

把动物泛称为光合作用主体不当，反应解释不完整。

## Prompt 4

Seed: 731004; automatic: FAIL; maximum 4-gram count: 4; coherent: True.

Prompt:
````text
Once upon a time, in a small village near the sea, there lived a
````

Exact continuation:
````text
 man named Gobindi. He was a very tall man, and he was very handsome. He was very smart and had a very good sense of humor. He was very good at making jokes and was very good at making jokes. He was very good at making jokes and was very good at making jokes. He
````

自然引入人物并描述特征，随后重复讲笑话的能力。

虚构叙述；未发展进一步情节。

## Prompt 5

Seed: 731005; automatic: FAIL; maximum 4-gram count: 3; coherent: False.

Prompt:
````text
The three main states of matter are
````

Exact continuation:
````text
 hydrogen, helium and carbon. The three main states of matter are: (1) the solid, (2) the liquid and (3) the gaseous. The solid state is the most stable of the three states of matter. The solid state is the most stable of the three states of matter. The solid state is
````

对同一三态先列元素，后列固液气，没有解释两套互相冲突的答案。

元素与物态混淆；固态总是最稳定的泛化不成立。

## Prompt 6

Seed: 731006; automatic: FAIL; maximum 4-gram count: 5; coherent: False.

Prompt:
````text
To make a cup of tea, first you need to
````

Exact continuation:
````text
 make a cup of tea. You can make a cup of tea by pouring a cup of tea into a cup of water. Then you can add a cup of water to the cup of tea. You can also add a cup of tea to the cup of water. You can also add a cup of tea to the cup
````

以已经泡好茶作为泡茶的前提，反复交换茶和水，没有有意义的操作顺序。

不能作为从原料开始的泡茶方法。

## Prompt 7

Seed: 731007; automatic: FAIL; maximum 4-gram count: 3; coherent: False.

Prompt:
````text
def fibonacci(n):
    """Return the nth Fibonacci number."""

````

Exact continuation:
````text
The Fibonacci numbers are a series of numbers that are used to represent the number of successive numbers in a sequence. The Fibonacci numbers are used to represent the number of successive numbers in a sequence. The Fibonacci numbers are used to represent the number of successive numbers in a sequence. The
````

函数声明和文档字符串后直接接未缩进英语说明，破坏代码续写结构。

无函数实现或返回值；没有执行生成代码。

## Prompt 8

Seed: 731008; automatic: FAIL; maximum 4-gram count: 3; coherent: False.

Prompt:
````text
The French Revolution began in 1789 because
````

Exact continuation:
````text
 of the French Revolution, which was a revolutionary movement that was led by the French Revolutionaries. The French Revolution was a period of political and social upheaval in France. The French Revolution was a period of political and social upheaval in France. The French Revolution was a period of political and social upheaval in France.
````

用法国大革命本身解释其发生，形成循环因果，随后重复背景句。

未给出有效成因解释。

## Prompt 9

Seed: 731009; automatic: FAIL; maximum 4-gram count: 5; coherent: True.

Prompt:
````text
Water boils at 100 degrees Celsius at sea level, but on a high mountain
````

Exact continuation:
````text
, it's 100 degrees. The water boils at 100 degrees Celsius at sea level, but on a high mountain, it's 100 degrees. The water boils at 100 degrees Celsius at sea level, but on a high mountain, it's 100 degrees. The water boils at
````

语言可理解且持续讨论两种海拔的沸点，但结论错误并反复重复。

没有体现较低气压下沸点降低。

## Prompt 10

Seed: 731010; automatic: FAIL; maximum 4-gram count: 6; coherent: True.

Prompt:
````text
A neural network learns by
````

Exact continuation:
````text
 analyzing the data it receives from the network. It learns by analyzing the data it receives from the network. It learns by analyzing the data it receives from the network. It learns by analyzing the data it receives from the network. It learns by analyzing the data it receives from the network. It learns by analyzing the data it
````

语法与主题衔接成立，但只重复同一笼统解释。

没有解释学习目标或参数更新，不能视为机制理解证据。

## Prompt 11

Seed: 731011; automatic: FAIL; maximum 4-gram count: 6; coherent: True.

Prompt:
````text
Dear Sir or Madam, I am writing to apply for the position of
````

Exact continuation:
````text
 the Secretary of State for the Commonwealth of Australia. I am a member of the Commonwealth Parliament and I am a member of the Commonwealth Parliament. I am a member of the Commonwealth Parliament and I am a member of the Commonwealth Parliament. I am a member of the Commonwealth Parliament and I am a member of the Commonwealth Parliament.
````

保持求职信口吻，随后反复重复身份声明。

职务与身份未核验，不作为真实事实。

## Prompt 12

Seed: 731012; automatic: FAIL; maximum 4-gram count: 18; coherent: False.

Prompt:
````text
One, two, three, four, five, six, seven,
````

Exact continuation:
````text
 eight, nine, ten, eleven, twelve, thirteen, fourteen, fifteen, sixteen, seventeen, eighteen, twenty, twenty, thirty, thirty, thirty, thirty, thirty, thirty, thirty, thirty, thirty, thirty, thirty, thirty, thirty, thirty, thirty, thirty, thirty, thirty, thirty,
````

最初接续数列，随后跳数并长期重复 thirty，失去序列规则。

漏十九、重复二十、跳到三十后循环。
