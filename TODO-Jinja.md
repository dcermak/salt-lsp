# TODO

* Change the SLS and Jinja Ast nodes to have a generic `children` field.
  This is needed to properly nest Jinja nodes within SLS ones.
  It means however providing convenience functions to look for all the current children without the Jinja nodes
* Implement the merge.
  See the TODO comments in the code, but the basic idea is to loop over the SLS tree and insert the Jinja nodes according to the position mapping.
* Add more unit tests!
* Test in real life to figure out if the whole parser is fault tolerant enough!

# Data to understand what's going on

This section shows what we get after each step for the following file:

```yaml
/etc/systemd/system/rootco-salt-backup.service:
  file.managed:
{% if pillar['user']|length() > 1 %}
    - user: {{ pillar['user'] }}
{% elif pillar['user']|length() == 1 %}
    - user: bar
{% else %}
    - user: foo
{% endif %}
{% for group in pillar['groups']%}
    - group: {{ group }}
{%- else %}
    - group: nobody
{% endfor %}

```

## Jinja AST ##

This is the result after having going through the jinja tokenizer and parser:

```py
jinja_ast = salt_lsp.jinja_parser.parse(salt_lsp.jinja_parser.tokenize(document))
```

result:
```
BranchNode(start=Position(line=0, col=0), end=Position(line=14, col=0), expression=None, expression_end=Position(line=14, col=0), body=[
    DataNode(start=Position(line=0, col=0), end=Position(line=2, col=0), data='/etc/systemd/system/rootco-salt-backup.service:\n  file.managed:\n'),
    BlockNode(start=Position(line=2, col=0), end=Position(line=8, col=11), kind='if', branches=[
        BranchNode(start=Position(line=2, col=0), end=Position(line=4, col=0), expression="{% if pillar['user']|length() > 1 %}", expression_end=Position(line=2, col=36), body=[
            DataNode(start=Position(line=2, col=36), end=Position(line=3, col=12), data='\n    - user: '),
            VariableNode(start=Position(line=3, col=12), end=Position(line=3, col=32), expression="{{ pillar['user'] }}"),
            DataNode(start=Position(line=3, col=32), end=Position(line=4, col=0), data='\n')]
        ),
        BranchNode(start=Position(line=4, col=0), end=Position(line=6, col=0), expression="{% elif pillar['user']|length() == 1 %}", expression_end=Position(line=4, col=39), body=[
            DataNode(start=Position(line=4, col=39), end=Position(line=6, col=0), data='\n    - user: bar\n')]
        ),
        BranchNode(start=Position(line=6, col=0), end=Position(line=8, col=0), expression='{% else %}', expression_end=Position(line=6, col=10), body=[
            DataNode(start=Position(line=6, col=10), end=Position(line=8, col=0), data='\n    - user: foo\n')]
        )], block_end_start=Position(line=8, col=0)
    ),
    DataNode(start=Position(line=8, col=11), end=Position(line=9, col=0), data='\n'),
    BlockNode(start=Position(line=9, col=0), end=Position(line=13, col=12), kind='for', branches=[
        BranchNode(start=Position(line=9, col=0), end=Position(line=11, col=0), expression="{% for group in pillar['groups']%}", expression_end=Position(line=9, col=34), body=[
            DataNode(start=Position(line=9, col=34), end=Position(line=10, col=13), data='\n    - group: '),
            VariableNode(start=Position(line=10, col=13), end=Position(line=10, col=24), expression='{{ group }}'),
            DataNode(start=Position(line=10, col=24), end=Position(line=11, col=0), data='\n')]
        ),
        BranchNode(start=Position(line=11, col=0), end=Position(line=13, col=0), expression='{%  else %}', expression_end=Position(line=11, col=11), body=[
            DataNode(start=Position(line=11, col=11), end=Position(line=13, col=0), data='\n    - group: nobody\n')]
        )], block_end_start=Position(line=13, col=0)
    ),
    DataNode(start=Position(line=13, col=12), end=Position(line=14, col=0), data='\n')]
)
```

## Generated YAML ##

After compiling the Jinja tree we get a YAML file obfuscating the Jinja parts like the following:

```yaml
/etc/systemd/system/rootco-salt-backup.service:
  file.managed:

    - user: ?? pillar['user'] ??

    - user: bar

    - user: foo


    - group: ?? group ??

    - group: nobody



```

## Position mapping ##

The position mapping provided by the compilation provides something of that sort:
```
{(2, 0): BranchNode(start=Position(line=2, col=0), end=Position(line=4, col=0), expression="{% if pillar['user']|length() > 1 %}", expression_end=Position(line=2, col=36), body=[...]),
 (4, 0): BranchNode(start=Position(line=4, col=0), end=Position(line=6, col=0), expression="{% elif pillar['user']|length() == 1 %}", expression_end=Position(line=4, col=39), body=[...]),
 (6, 0): BranchNode(start=Position(line=6, col=0), end=Position(line=8, col=0), expression='{% else %}', expression_end=Position(line=6, col=10), body=[...]),
 (8, 0): BlockNode(start=Position(line=2, col=0), end=Position(line=8, col=11), kind='if', branches=[...], block_end_start=Position(line=8, col=0)),
 (9, 0): BranchNode(start=Position(line=9, col=0), end=Position(line=11, col=0), expression="{% for group in pillar['groups']%}", expression_end=Position(line=9, col=34), body=[...]),
 (11, 0): BranchNode(start=Position(line=11, col=0), end=Position(line=13, col=0), expression='{%  else %}', expression_end=Position(line=11, col=11), body=[...]),
 (13, 0): BlockNode(start=Position(line=9, col=0), end=Position(line=13, col=12), kind='for', branches=[...], block_end_start=Position(line=13, col=0))}
```

## YAML AST ##

Parsing the YAML document with the SLS parser provides the following AST:
```
Tree(start=Position(line=0, col=0), end=Position(line=14, col=0), includes=None, extend=None, states=[
    StateNode(start=Position(line=0, col=0), end=Position(line=14, col=0), identifier='/etc/systemd/system/rootco-salt-backup.service', states=[
        StateCallNode(start=Position(line=1, col=2), end=Position(line=14, col=0), name='file.managed', parameters=[
            StateParameterNode(start=Position(line=3, col=4), end=Position(line=5, col=4), name='user', value="?? pillar['user'] ??"),
            StateParameterNode(start=Position(line=5, col=4), end=Position(line=7, col=4), name='user', value='bar'),
            StateParameterNode(start=Position(line=7, col=4), end=Position(line=10, col=4), name='user', value='foo'),
            StateParameterNode(start=Position(line=10, col=4), end=Position(line=12, col=4), name='group', value='?? group ??'),
            StateParameterNode(start=Position(line=12, col=4), end=Position(line=14, col=0), name='group', value='nobody')], requisites=[]
        )]
    )]
)
```
 
### Expected merged tree ###

Of course this is still not implemented, but here is how the merged tree should approximately look like:

```
Tree(start=Position(line=0, col=0), end=Position(line=14, col=0), includes=None, extend=None, children=[
    StateNode(start=Position(line=0, col=0), end=Position(line=14, col=0), identifier='/etc/systemd/system/rootco-salt-backup.service', children=[
        StateCallNode(start=Position(line=1, col=2), end=Position(line=14, col=0), name='file.managed', children=[
            BlockNode(start=Position(line=2, col=0), end=Position(line=8, col=11), kind='if', block_end_start=Position(line=8, col=0), children=[
                BranchNode(start=Position(line=2, col=0), end=Position(line=4, col=0), expression="{% if pillar['user']|length() > 1 %}", expression_end=Position(line=2, col=36), children=[
                    StateParameterNode(start=Position(line=3, col=4), end=Position(line=4, col=0), name='user', value="{{ pillar['user'] }}")]
                ),
                BranchNode(start=Position(line=4, col=0), end=Position(line=6, col=0), expression="{% elif pillar['user']|length() == 1 %}", expression_end=Position(line=4, col=39), children=[
                    StateParameterNode(start=Position(line=5, col=4), end=Position(line=6, col=0), name='user', value='bar')]
                ),
                BranchNode(start=Position(line=6, col=0), end=Position(line=8, col=0), expression='{% else %}', expression_end=Position(line=6, col=10), children=[
                    StateParameterNode(start=Position(line=7, col=4), end=Position(line=8, col=11), name='user', value='foo')]
                )],
            ),
            BlockNode(start=Position(line=9, col=0), end=Position(line=13, col=12), kind='for', block_end_start=Position(line=13, col=0), children=[
                BranchNode(start=Position(line=9, col=0), end=Position(line=11, col=0), expression="{% for group in pillar['groups']%}", expression_end=Position(line=9, col=34), children=[
                    StateParameterNode(start=Position(line=10, col=4), end=Position(line=11, col=0), name='group', value='{{ group }}')]
                ),
                BranchNode(start=Position(line=11, col=0), end=Position(line=13, col=0), expression='{%  else %}', expression_end=Position(line=11, col=11), children=[
                    StateParameterNode(start=Position(line=12, col=4), end=Position(line=14, col=0), name='group', value='nobody')]
                )],
            )]        
        )]
    )]
)
```
