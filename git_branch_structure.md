# Git Branch Structure for ISRO Help Bot

## Main Branches

### `master` (or `main`)
- The primary branch containing production-ready code
- Protected branch - no direct pushes
- Only accepts merges through pull requests
- Requires code review before merging

### `developer-1`
- Working branch for Developer 1 (Search & Content Features)
- Feature development and testing
- Branches off from master
- Regular commits and updates

## Branch Usage Guidelines

### Initial Setup
```bash
# Initial repository setup
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/[username]/isro-helpbot.git
git push -u origin main

# Create developer branch
git checkout -b developer-1
git push -u origin developer-1
```

### Development Workflow
1. Always pull latest changes from main
```bash
git checkout main
git pull origin main
git checkout developer-1
git merge main
```

2. Make changes in developer-1 branch
```bash
git add .
git commit -m "feature: description of changes"
git push origin developer-1
```

3. Create Pull Request to main
- Create PR through GitHub interface
- Add description of changes
- Request code review
- Merge after approval

## Branch Protection Rules
1. `main` branch:
   - Require pull request reviews
   - Require status checks to pass
   - No direct pushes
   - Up-to-date before merging

2. `developer-1` branch:
   - Allow force push
   - Regular backups
   - Direct commits allowed

## Commit Message Format
```
type(scope): description

Types:
- feat: New feature
- fix: Bug fix
- docs: Documentation
- style: Formatting
- refactor: Code restructuring
- test: Adding tests
- chore: Maintenance
```

## Development Rules
1. Create feature-specific branches from developer-1 if needed
2. Regular commits with clear messages
3. Daily pushes to remote
4. Code review before merging to main
5. Keep branches synchronized