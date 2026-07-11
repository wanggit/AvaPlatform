# Skill packages are uploaded as ZIP artifacts

Skill Library stores each Skill as an uploaded `.zip` Skill Package rather than as individually managed files in the admin UI. A package must contain `SKILL.md` and may contain supporting files such as scripts, references, templates, and assets.

**Why**: Hermes consumes Skills as filesystem directories, not as a database-native form. Treating the uploaded package as the versioned artifact preserves the Hermes-native layout, supports multi-file Skills, and gives the Platform a clean unit for review, publishing, distribution, audit, and rollback.

**Consequences**: the admin backend does not expose a file-count field and does not provide file-level Skill editing in the MVP. When a Skill is bound to a Job Template and instantiated for a Digital Employee, the Instance Manager expands or copies the package into that employee's Profile `skills/{skill_name}/` directory.
