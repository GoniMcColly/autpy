# CONTRIBUTING

```sh
git clone -o gh git@github.com:cvanloo/autpy.git && cd autpy
```

Make sure to [sign](https://calebhearth.com/sign-git-with-ssh) your commits.

1. **Create an Issue first**
   Whether it's about a bug or a feature, your first step should be to open an issue.
   You can use this issue to document your thought process and any problems you may encounter.
   This way other contributors can see what you are working on and changes can be discussed early.

2. **Commit changes to a private branch**
   ```sh
   git switch -c feature-XXX
   ```
   Commit often. The commit message should adequately describe the changes and
   be written in present tense.
   You should generally follow these [conventions](https://www.conventionalcommits.org/en/v1.0.0/).
   ```sh
   git commit -m "feat(cors): handle options and preflight in middleware"
   ```

3. **Create a Pull Request**
   Once your changeset is finished and all tests are passing, publish your branch and create a PR.
   But first make sure that your code is formatted correctly (use a linter/autoformatter!).
   (It's called Python and not Camel, so please use\_snake\_case\_consistently.)

   To avoid merge conflicts, first *rebase* your feature branch on top of `main`.
   ```sh
   # with your 'feature-XXX' branch checked out:
   git fetch gh
   git rebase gh/main
   ```
   Now's the time to clean up your commit history, reword commit messages, or
   squash multiple commits into one.

   Finally, publish your branch...
   ```sh
   git push -u gh feature-XXX
   ```
   ...and create a Pull Request.

   **Do not rebase public branches!**
   Now that your branch is public, others might check it out and add their own
   commits.
   If you rebase a public branch and force push, you're only causing trouble.

4. **Await approval and merge**
   Once all checks have passed and the changes been reviewed, the PR can be merged.
   Tip: if you include a note at the bottom of the merge message like "closes
   #5" GitHub will automatically close the associated issue for you (replace #5 with the correct ID).

   For your next contribution, remember to create a new branch starting from `main`.

Happy hacking!
