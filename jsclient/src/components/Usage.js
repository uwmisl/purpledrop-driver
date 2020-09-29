import React from 'react';

class Usage extends React.Component {
  render() {
    return <div>
      <h3>Shortcut Keys</h3>
      <p>
        <ul>
          <li>Shift-click: Add electrodes to active list</li>
          <li>Ctrl-click: Remove electrodes from active list</li>
          <li>ESC: Deactivate all electrodes</li>
          <li>Arrow keys: Move activated electrodes as a group</li>
        </ul>
      </p>
    </div>;
  }
}

export default Usage;