# DeviantArt Import Scraper

## Instructions

1. Download `scraper.exe` from the latest release.

2. Run the `scraper.exe` file.

3. DeviantArt will be opened in your browser. You will need to authenticate your account to proceed. The next steps will be completed in the terminal.

4. **Enter the output file name (exclude extension):** `testname`
    
    *This will be the name of your .tsv file. When the scraper has finished, this will be saved in the same directory as your executable.*

5. **Enter the DeviantArt username:** `username`

6. **Do you want to include all folders? (y/n)** `y/yes or n/no`

    *If you enter `y/yes`, deviations will be copied from the user's entire gallery. There will be no more prompts. If `n/no` is entered, you will specify the folders to copy from in step 4.*

7. **Available folders:**

    **Folder ID: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX, Folder Name: Featured**

    **Include 'Featured' in the data copy? (y/n)** `y/yes or n/no`

    *If you enter `y/yes`, deviations will be copied from this folder, otherwise they will be skipped.*

    *This will loop through all available folders. Subfolders will only be checked if their parent folder is included.*

8. **Wrote deviation data to `testname`.tsv**

    *Scraping is completed! You can find your deviation data in the newly created .tsv file. You can close out the application and your browser tab.*