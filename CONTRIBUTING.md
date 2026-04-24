# Contributing to AI Clip Creator

Thank you for your interest in contributing to AI Clip Creator! This document provides guidelines and instructions for contributing.

## 🎉 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [How to Contribute](#how-to-contribute)
- [Development Setup](#development-setup)
- [Coding Standards](#coding-standards)
- [Pull Request Process](#pull-request-process)
- [Community](#community)

---

## 🚀 Getting Started

### Prerequisites

- Python 3.9 or higher
- Git
- (Optional) GPU with CUDA/DirectML support

### Fork & Clone

1. **Fork** the repository on GitHub
2. **Clone** your fork locally:
   ```bash
   git clone https://github.com/ramasanjaya3302/AI-clip-creator.git
   cd AI-clip-creator
   ```
3. **Add upstream** remote:
   ```bash
   git remote add upstream https://github.com/ramasanjaya3302/AI-clip-creator.git
   ```

---

## 💻 Development Setup

### Create Virtual Environment

```bash
# Windows
python -m venv venv312
.\venv312\Scripts\activate

# Linux / macOS
python3 -m venv venv312
source venv312/bin/activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Download Model Files

Ensure these files exist in `models/` directory:
- `VideoAutoClipper.pt` - Pre-trained PyTorch model
- `mfcc_scaler.joblib` - MFCC feature scaler

If you don't have the model files, set `"auto_load_model": false` in `config.json`.

### Run the Application

```bash
python main.py
```

Access at: http://localhost:5000

---

## 🤖 How to Contribute

### Reporting Bugs

1. Check [existing issues](https://github.com/yourusername/AI-clip-creator/issues) first
2. Use the [Bug Report template](https://github.com/yourusername/AI-clip-creator/issues/new?template=bug_report.md)
3. Include:
   - Steps to reproduce
   - Expected vs actual behavior
   - Screenshots if applicable
   - System information (OS, Python version, GPU)

### Suggesting Features

1. Check [existing feature requests](https://github.com/yourusername/AI-clip-creator/issues?q=is%3Aissue+label%3Aenhancement)
2. Use the [Feature Request template](https://github.com/yourusername/AI-clip-creator/issues/new?template=feature_request.md)
3. Describe:
   - Problem you're trying to solve
   - Proposed solution
   - Alternative approaches considered

### Submitting Code

1. **Create a branch**:
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/your-bug-fix
   ```

2. **Make your changes**
   - Follow coding standards (see below)
   - Keep commits atomic and focused
   - Write clear commit messages

3. **Test your changes**:
   ```bash
   # Add tests if applicable
   # Test manually with various video formats
   ```

4. **Commit your changes**:
   ```bash
   git add .
   git commit -m "Add: your descriptive commit message"
   ```

5. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Create a Pull Request** on GitHub

---

## 📏 Coding Standards

### Python Style

- Follow [PEP 8](https://pep8.org/) style guide
- Use type hints where appropriate
- Write docstrings for functions and classes
- Keep functions focused and small (< 50 lines when possible)

### Documentation

- Update README.md if adding user-facing features
- Add docstrings to new functions/classes
- Update API documentation for endpoint changes
- Include code comments for complex logic

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat:` - New features
- `fix:` - Bug fixes
- `docs:` - Documentation changes
- `style:` - Code style/formatting
- `refactor:` - Code refactoring
- `test:` - Adding or updating tests
- `chore:` - Build process or auxiliary tool changes

**Examples:**
```bash
feat(clip-editor): add support for 4K video export
fix(api): resolve memory leak in export endpoint
docs(readme): update installation instructions for macOS
```

---

## 🚀 Pull Request Process

### Before Submitting

- [ ] Code follows project coding standards
- [ ] Self-review of code completed
- [ ] Comments added for complex logic
- [ ] Documentation updated (if needed)
- [ ] Tests added/updated (if applicable)
- [ ] All tests passing
- [ ] No merge conflicts

### PR Description Template

```markdown
## Description
Brief description of changes made.

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Refactoring
- [ ] Performance improvement

## Testing
Describe how you tested your changes.

## Screenshots (if applicable)
Add screenshots for UI changes.

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-reviewed
- [ ] Documentation updated
- [ ] Tests added (if applicable)
```

### Review Process

1. Maintainers will review your PR
2. Address any feedback or requested changes
3. Once approved, your PR will be merged
4. Celebrate! 🎉

---

## 🌐 Community

### Getting Help

- [GitHub Discussions](https://github.com/yourusername/AI-clip-creator/discussions) - General questions
- [GitHub Issues](https://github.com/yourusername/AI-clip-creator/issues) - Bug reports & feature requests
- [Discord Server](https://discord.gg/sneaclip) - Real-time chat

### Recognition

Contributors are recognized in:
- Release notes for significant contributions
- Contributors page on the website (coming soon)
- Annual contributor spotlight

---

## 📜 License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

**Thank you for contributing to AI Clip Creator! 🎬**
