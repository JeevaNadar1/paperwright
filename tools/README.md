# tools

`validate_skill.py` is vendored from [skill-god](https://github.com/JeevaNadar1)
(MIT) so that CI can lint this skill without depending on another checkout.
It checks frontmatter, name rules, description strength, line and token budgets,
dead links, orphan references, script syntax and mandate spam.

```bash
python3 tools/validate_skill.py skills/paperwright --strict
```
