import { registerRootComponent } from 'expo';
import App from './App';

// Точка входа Expo. registerRootComponent регистрирует корневой компонент и
// корректно настраивает окружение и в Expo Go, и в нативной сборке.
registerRootComponent(App);
