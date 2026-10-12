import fs from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import openapiTS from 'openapi-typescript';

const contract = new URL('../../../contracts/openapi.json', import.meta.url);
const output = new URL('../src/api/openapi.ts', import.meta.url);
const generated = await openapiTS(fileURLToPath(contract));
if (process.argv.includes('--check')) {
    if ((await fs.readFile(output, 'utf8')) !== generated) {
        console.error('API types have drifted. Run npm run generate:api.');
        process.exitCode = 1;
    }
} else {
    await fs.writeFile(output, generated);
}
