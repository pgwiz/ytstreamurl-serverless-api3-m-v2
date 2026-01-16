import ytsr from '@distube/ytsr';

async function debugSearch() {
    try {
        const searchResults = await ytsr('rick astley', { limit: 1 });
        console.log(JSON.stringify(searchResults.items[0], null, 2));
    } catch (error) {
        console.error(error);
    }
}

debugSearch();
