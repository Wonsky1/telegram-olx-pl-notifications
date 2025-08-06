# Prioritized Improvements & Bugs

Below is the recommended order for tackling improvements and bug fixes. Each item is listed by priority (highest first):

2. **Persist states in Redis/PostgreSQL**  
   Ensures state is durable and sharable across instances.
3. **Add automated tests**  
   Enables safe refactoring and reliable deployments.
4. **Introduce a staging flow**  
   Allows safe validation before production deploys.
5. **Add autodeploy (CI/CD)**  
   Automates releases once tests and staging are in place.
6. **Make custom prompts configurable**  
   Improves UX after system stability is ensured.
7. **Add support for other languages**  
   Expands user base after core system is robust.

Maybe transfer DB module to some separate web server? backend
