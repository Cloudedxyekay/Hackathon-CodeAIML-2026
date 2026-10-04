import { mergeConfig } from 'vite';
import original from '../vite.config.js';
export default mergeConfig(original, {server: {port: 5174, strictPort: true, proxy: {'/api': 'http://127.0.0.1:8010'}}});
