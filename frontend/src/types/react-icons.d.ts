// Allow importing icon sets from 'react-icons/<set>' subpaths
// Some project TypeScript setups can't resolve subpath declarations; this file
// provides fallback module declarations so imports like 'react-icons/fa' work.

declare module 'react-icons/*' {
  import * as React from 'react';
  import { IconBaseProps } from 'react-icons';
  export type IconType = React.ComponentType<IconBaseProps>;
  const icons: { [key: string]: IconType };
  export default icons;
}

declare module 'react-icons/fa';
